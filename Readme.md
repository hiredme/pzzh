# Ework - AI英语作文智能批改平台

## 项目简介
Ework是一个基于Django的AI英语作文智能批改平台，集成DeepSeek自然语言处理API，提供专业的英语作文评分、错误批改和语法建议。系统支持文本文件上传，实现从OCR识别（预留接口）到智能批改的全流程自动化处理。

## 主要特性
✅ **用户认证系统**  
- 完整的注册/登录流程
- 基于装饰器的访问控制（@login_required）
- 自定义用户模型扩展

📝 **智能批改功能**  
- 多格式文件上传（当前支持.txt）
- 同步/异步处理模式（Celery任务队列）
- 四维评分体系：拼写/语法/连贯性/词汇
- 精准错误定位（起始位置标记）
- AI修改建议（置信度指标）

📊 **数据可视化**  
- 交互式评分雷达图
- 分页提交历史记录
- 实时处理状态追踪
- 系统操作日志审计

⚙️ **技术增强**  
- 原子化事务处理
- 指数退避重试机制
- 数据库查询优化（Prefetch）
- 安全异常处理
- Decimal精确计算

## 技术栈
**核心框架**  
- Django 4.2
- Celery 5.3
- DeepSeek API

**前端架构**  
- Bootstrap 5
- 响应式布局
- 动态数据渲染

**数据库**  
- PostgreSQL / MySQL
- 关系模型优化
- 事务性写入

## 快速部署
```bash
# 克隆仓库
git clone https://github.com/yourrepo/ework.git

# 安装依赖
python -m pip install -r requirements.txt

#创建local_settings.py
#内容为如下：
DEEPSEEK_API = {
    "API_URL": "https://api.deepseek.com/v1/chat/completions",
    "API_KEY": "your_apikey",
    "TIMEOUT": 600,  # 请求超时时间
    "RETRIES": 3,  }

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 启动服务
celery -A ework worker --loglevel=info &
python manage.py runserver