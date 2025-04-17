from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

from local_settings import DEEPSEEK_API
from .models import Submission, Score
from django.contrib import messages
from .forms import UploadForm
from .forms import CustomUserCreationForm
from django.core.paginator import Paginator
from django.conf import settings
from celery import shared_task
import time
import requests
from django.shortcuts import get_object_or_404
from .models import Submission, Score, Essay, Correction, SystemLog
from celery import shared_task
import requests
from django.conf import settings
from .models import Submission, Essay, Score, Correction, SystemLog
from django.db import transaction, IntegrityError
import json
from decimal import Decimal
from django.utils import timezone


def index(request):
    recent_submissions = []  # 初始化空列表

    if request.user.is_authenticated:
        recent_submissions = (
            Submission.objects.filter(user=request.user)
            .select_related("essay")
            .prefetch_related("essay__score")
            .order_by("-upload_time")[:5]
        )

    context = {
        "recent_submissions": recent_submissions,
    }
    return render(request, "index.html", context)


def process_submission_sync(submission_id):
    try:
        submission = Submission.objects.get(id=submission_id)

        # 获取待处理文本
        raw_text = extract_text(submission.original_file)

        # API调用处理
        api_response = call_deepseek_api(raw_text)
        processed_data = parse_deepseek_response(api_response)

        # 数据持久化
        save_processing_results(submission, raw_text, processed_data)

        submission.status = "completed"
        submission.save(update_fields=["status"])
        return True

    except Exception as e:
        submission.status = "failed"
        submission.save(update_fields=["status"])
        SystemLog.objects.create(
            log_type="SYSTEM",
            submission=submission,
            message=f"同步处理失败: {str(e)}",
        )
        raise  # 将异常抛给视图函数


@login_required
def upload(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 保存提交记录
                submission = form.save(commit=False)
                submission.user = request.user
                submission.file_size = request.FILES["original_file"].size // 1024
                submission.status = "processing"  # 直接改为处理中
                submission.save()  # 提前保存状态

                # 改为同步处理
                process_submission_sync(submission.id)  # 调用同步处理函数

                messages.success(request, "文件处理完成")
                return redirect("submission_detail", submission_id=submission.id)
            except Exception as e:
                submission.status = "failed"  # 记录失败状态
                submission.save()
                messages.error(request, f"处理失败：{str(e)}")
        else:
            messages.error(request, "表单验证失败，请检查输入")
    else:
        form = UploadForm()

    return render(request, "upload.html", {"form": form})


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]  # 处理额外字段
            user.save()
            messages.success(request, "注册成功！请登录")
            return redirect("login")
    else:
        form = CustomUserCreationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def submission_history(request):
    submissions_list = Submission.objects.filter(user=request.user).order_by(
        "-upload_time"
    )

    # 分页（每页10条）
    paginator = Paginator(submissions_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "submission_history.html",
        {
            "page_obj": page_obj,
        },
    )


@login_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(Submission, pk=submission_id, user=request.user)
    essay = Essay.objects.filter(submission=submission).first()

    # 获取关联数据
    score = Score.objects.filter(essay=essay).first() if essay else None
    corrections = Correction.objects.filter(essay=essay) if essay else []
    logs = SystemLog.objects.filter(submission=submission)

    # 构造评分数据结构
    score_data = []
    if score:
        score_data = [
            ("拼写", score.spelling, "primary"),
            ("语法", score.grammar, "success"),
            ("连贯性", score.cohesion, "info"),
            ("词汇", score.vocabulary, "warning"),
        ]

    context = {
        "submission": submission,
        "essay": essay,
        "score": score,
        "score_data": score_data,  # 添加构造好的数据结构
        "corrections": corrections,
        "logs": logs,
    }
    return render(request, "submission_detail.html", context)


from celery import shared_task
import requests
from django.conf import settings
from .models import Submission, Essay, Score, Correction, SystemLog




@shared_task(bind=True, max_retries=DEEPSEEK_API.get("RETRIES", 3))
def process_submission_task(self, submission_id):
    try:

        submission = Submission.objects.get(id=submission_id)
        submission.status = "processing"
        submission.save(update_fields=["status"])

        # 获取待处理文本
        raw_text = extract_text(submission.original_file)

        # API调用处理
        api_response = call_deepseek_api(raw_text)
        processed_data = parse_deepseek_response(api_response)

        # 数据持久化
        save_processing_results(submission, raw_text, processed_data)

        submission.status = "completed"
        submission.save(update_fields=["status"])
        return True

    except Submission.DoesNotExist:
        SystemLog.objects.create(
            log_type="SYSTEM", message=f"无效的提交ID: {submission_id}"
        )
        return False

    except (requests.ConnectionError, requests.Timeout) as e:
        return handle_retryable_error(self, submission, e, "API连接失败")

    except requests.HTTPError as e:
        error_msg = f"API请求错误[{e.response.status_code}]: {e.response.text[:200]}"
        return handle_retryable_error(self, submission, e, error_msg)

    except (ValueError, RuntimeError, KeyError) as e:
        submission.status = "failed"
        submission.save(update_fields=["status"])
        SystemLog.objects.create(
            log_type="DATA",
            submission=submission,
            message=f"数据处理失败: {str(e)}",
        )
        return False

    except Exception as e:
        SystemLog.objects.create(
            log_type="SYSTEM",
            submission=submission,
            message=f"未处理异常: {str(e)}",
        )
        raise


def extract_text(file):
    """安全处理文件内容提取"""
    try:
        if file.name.endswith(".txt"):
            # 确保文件指针在开头
            file.seek(0)
            content = file.read().decode("utf-8")
            # 清理可能的BOM头
            return content.lstrip("\ufeff")
        raise ValueError("暂不支持的文件格式")
    except UnicodeDecodeError:
        raise RuntimeError("文件编码错误（请使用UTF-8编码）")
    except AttributeError:
        raise RuntimeError("无效的文件对象")


def call_deepseek_api(text):
    """执行带重试机制的API调用"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API['API_KEY']}",
        "Content-Type": "application/json",
    }
    text1 = """
你是一个经验丰富，态度严苛的英语作文批改机器，接下来你将处理一篇作文，请根据以下规定输出文字。
1.输出格式为json，格式如下：
{
"scores": {
"total_score": 数值,
"spelling": 数值,
"grammar": 数值,
"cohesion": 数值,
"vocabulary": 数值,
"comments": "综合评价文本，请使用中文"
},
"corrections": [
{
"error_type": "拼写错误/spelling | 语法错误/grammar | 搭配错误/collocation | 标点错误/punctuation",
"start_pos": 起始位置数字,
"end_pos": 结束位置数字,
"original_text": "错误文本片段",
"suggestion": "修改建议文本,请使用中文",
"confidence": 置信度浮点数
},
// 更多错误条目...
]
}

2.除了要求输出的json外，什么都不要输出。
3.回答之前请仔细检查：

错误类型必须使用英文键值（spelling/grammar/collocation/punctuation）

位置数字从0开始计数

confidence取值范围0.0-1.0

分数保留1位小数

确保所有字段名称与示例完全一致
4.示例输出结构：
{
"scores": {
"total_score": 85.5,
"spelling": 18.0,
"grammar": 22.5,
"cohesion": 20.0,
"vocabulary": 25.0,
"comments": "文章结构清晰，但需注意动词时态一致性..."
},
"corrections": [
{
"error_type": "grammar",
"start_pos": 45,
"end_pos": 52,
"original_text": "she go",
"suggestion": "修改为she goes",
"confidence": 0.98
},
{
"error_type": "punctuation",
"start_pos": 78,
"end_pos": 79,
"original_text": ",",
"suggestion": "修改为.",
"confidence": 1.0
}
]
}
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": text1},
            {"role": "user", "content": text},
        ],
        "temperature": 0.5,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        DEEPSEEK_API["API_URL"],
        headers=headers,
        json=payload,
        timeout=DEEPSEEK_API.get("TIMEOUT", 300),
    )
    response.raise_for_status()
    json_response = response.json()
    return json_response


def parse_deepseek_response(api_data):
    """
    解析Deepseek API响应数据，提取结构化批改结果
    :param api_data: API返回的原始数据（字典格式）
    :return: 包含格式化scores和corrections的字典
    """
    try:
        # 提取JSON响应内容
        content_str = api_data["choices"][0]["message"]["content"]
        result = json.loads(content_str)

        # 初始化返回结构
        parsed_data = {"scores": None, "corrections": []}

        # 解析分数部分
        if "scores" in result:
            scores = result["scores"]
            parsed_data["scores"] = {
                "total_score": Decimal(str(scores["total_score"])).quantize(
                    Decimal("0.0")
                ),
                "spelling": Decimal(str(scores["spelling"])).quantize(Decimal("0.0")),
                "grammar": Decimal(str(scores["grammar"])).quantize(Decimal("0.0")),
                "cohesion": Decimal(str(scores["cohesion"])).quantize(Decimal("0.0")),
                "vocabulary": Decimal(str(scores["vocabulary"])).quantize(
                    Decimal("0.0")
                ),
                "comments": scores["comments"],
            }

        # 解析批改详情
        if "corrections" in result:
            for correction in result["corrections"]:
                parsed_data["corrections"].append(
                    {
                        "error_type": correction["error_type"],
                        "start_pos": int(correction["start_pos"]),
                        "end_pos": int(correction["end_pos"]),
                        "original_text": correction["original_text"],
                        "suggestion": correction["suggestion"],
                        "confidence": float(correction["confidence"]),
                    }
                )

        return parsed_data

    except KeyError as e:
        raise ValueError(f"缺少必要字段: {str(e)}") from e
    except json.JSONDecodeError as e:
        raise ValueError("无效的JSON格式") from e
    except Exception as e:
        raise RuntimeError(f"解析失败: {str(e)}") from e


def save_processing_results(submission, raw_text, processed_data):
    """ """
    try:
        with transaction.atomic():
            # 创建Essay记录（需要解决language_level来源问题）
            essay = Essay.objects.create(
                submission=submission,
                raw_text=raw_text,
                processed_text=processed_data.get(
                    "processed_text", raw_text
                ),  # 临时方案
                language_level="P3",  # 需要实际数据源，此处为示例
                extract_time=timezone.now(),
            )

            # 创建Score记录
            score_data = processed_data["scores"]
            Score.objects.create(
                essay=essay,
                total_score=score_data["total_score"],
                spelling=score_data["spelling"],
                grammar=score_data["grammar"],
                cohesion=score_data["cohesion"],
                vocabulary=score_data["vocabulary"],
                comments=score_data["comments"],
                engine_used="deepseek",
            )

            # 批量创建Correction记录
            corrections = [
                Correction(
                    essay=essay,
                    error_type=cor["error_type"],
                    start_pos=cor["start_pos"],
                    end_pos=cor["end_pos"],
                    original_text=cor["original_text"],
                    suggestion=cor["suggestion"],
                    confidence=cor["confidence"],
                )
                for cor in processed_data["corrections"]
            ]
            Correction.objects.bulk_create(corrections)

            # 记录日志
            SystemLog.objects.create(
                log_type="AI", submission=submission, message="作文处理完成"
            )

    except KeyError as e:
        raise ValueError(f"缺失必要字段: {str(e)}")
    except IntegrityError as e:
        raise RuntimeError(f"数据完整性错误: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"保存失败: {str(e)}")


def handle_retryable_error(task, submission, error, message):
    """统一处理可重试错误"""
    submission.status = "failed"
    submission.save(update_fields=["status"])

    SystemLog.objects.create(
        log_type="API", submission=submission, message=f"{message}: {str(error)}"
    )

    retry_count = task.request.retries
    countdown = 60 * (2**retry_count)  # 指数退避
    raise task.retry(exc=error, countdown=min(countdown, 600))  # 最长等待10分钟
