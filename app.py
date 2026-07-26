"""
向后兼容入口点

推荐通过 Gunicorn 使用 app:create_app() 工厂函数启动。
开发环境可直接运行: python app.py
"""
from app import create_app

# 导出供 Gunicorn 使用: gunicorn "app:create_app()"
# 无需在此创建实例，避免副作用

if __name__ == "__main__":
    # 开发模式直接运行
    import os
    os.environ.setdefault("FLASK_ENV", "development")
    app = create_app("development")
    app.run(debug=True, host="0.0.0.0", port=5000)
