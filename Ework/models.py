from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# 用户模型（替换默认用户模型）
class User(AbstractUser):
    email = models.EmailField('邮箱', blank=True)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['username']),
        ]

# 文件提交模型
class Submission(models.Model):
    FILE_TYPE_CHOICES = (
        ('image', '图片'),
        ('doc', '文档'),
        ('txt', '文本')
    )
    
    STATUS_CHOICES = (
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    file_type = models.CharField('文件类型', max_length=5, choices=FILE_TYPE_CHOICES)
    original_file = models.FileField('原始文件', upload_to='submissions/%Y/%m/%d/')
    file_size = models.IntegerField('文件大小(KB)')
    upload_time = models.DateTimeField('上传时间', auto_now_add=True)
    ocr_used = models.BooleanField('OCR处理', default=False)
    status = models.CharField(
        '处理状态',
        max_length=20,  # 统一长度
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True  # 添加索引
    )


    class Meta:
        db_table = 'submissions'
        indexes = [
            models.Index(fields=['user', 'upload_time']),
        ]

# 作文文本模型
class Essay(models.Model):
    GRADE_CHOICES = (
        ('P1', '一年级'),
        ('P2', '二年级'),
        ('P3', '三年级'),
        ('P4', '四年级'),
        ('P5', '五年级'),
        ('P6', '六年级'),
    )

    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, verbose_name='提交记录')
    raw_text = models.TextField('原始文本')
    processed_text = models.TextField('处理后文本')
    language_level = models.CharField('适用年级', max_length=2, choices=GRADE_CHOICES)
    extract_time = models.DateTimeField('提取时间', auto_now_add=True)

    class Meta:
        db_table = 'essays'

# 批改明细模型
class Correction(models.Model):
    ERROR_TYPES = (
        ('spelling', '拼写错误'),
        ('grammar', '语法错误'),
        ('collocation', '搭配错误'),
        ('punctuation', '标点错误'),
    )

    essay = models.ForeignKey(Essay, on_delete=models.CASCADE, verbose_name='对应作文')
    error_type = models.CharField('错误类型', max_length=12, choices=ERROR_TYPES)
    start_pos = models.IntegerField('起始位置')
    end_pos = models.IntegerField('结束位置')
    original_text = models.CharField('错误内容', max_length=255)
    suggestion = models.CharField('修改建议', max_length=255)
    confidence = models.FloatField('置信度')

    class Meta:
        db_table = 'corrections'
        indexes = [
            models.Index(fields=['essay', 'error_type']),
        ]

# 综合评分模型
class Score(models.Model):
    essay = models.OneToOneField(Essay, on_delete=models.CASCADE, verbose_name='对应作文')
    total_score = models.DecimalField('总分', max_digits=4, decimal_places=1)
    spelling = models.DecimalField('拼写分', max_digits=3, decimal_places=1)
    grammar = models.DecimalField('语法分', max_digits=3, decimal_places=1)
    cohesion = models.DecimalField('连贯性', max_digits=3, decimal_places=1)
    vocabulary = models.DecimalField('词汇分', max_digits=3, decimal_places=1)
    comments = models.TextField('综合评价')
    engine_used = models.CharField('分析引擎', max_length=20)

    class Meta:
        db_table = 'scores'

# 批改报告模型
class Report(models.Model):
    essay = models.OneToOneField(Essay, on_delete=models.CASCADE, verbose_name='对应作文')
    html_content = models.TextField('HTML内容')
    json_data = models.JSONField('结构化数据')
    generated_at = models.DateTimeField('生成时间', auto_now_add=True)

    class Meta:
        db_table = 'reports'

# 系统日志模型
class SystemLog(models.Model):
    LOG_TYPES = (
        ('OCR', 'OCR处理'),
        ('AI', 'AI分析'),
        ('SYSTEM', '系统日志'),
    )

    log_type = models.CharField(
        '日志类型',
        max_length=20,  # 注意：长度需足够包含最长选项（如'SYSTEM'）
        choices=LOG_TYPES,
        db_index=True
    )
    submission = models.ForeignKey(
        Submission, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    message = models.TextField('日志内容')  # 正确字段名应为 message
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = 'system_logs'

# 词汇库模型
class Vocabulary(models.Model):
    GRADE_CHOICES = (
        ('P1', '一年级'),
        ('P2', '二年级'),
        ('P3', '三年级'),
        ('P4', '四年级'),
        ('P5', '五年级'),
        ('P6', '六年级'),
    )

    word = models.CharField('单词', max_length=50, unique=True)
    grade_level = models.CharField('适用年级', max_length=2, choices=GRADE_CHOICES)
    part_of_speech = models.CharField('词性', max_length=20)
    example_usage = models.CharField('示例用法', max_length=255)

    class Meta:
        db_table = 'vocabulary'