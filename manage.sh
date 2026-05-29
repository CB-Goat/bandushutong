#!/bin/bash
# Reading Companion 管理脚本
# 用法: ./manage.sh [start|stop|restart|logs|status]

case "$1" in
    start)
        echo "启动服务..."
        docker-compose up -d
        ;;
    stop)
        echo "停止服务..."
        docker-compose down
        ;;
    restart)
        echo "重启服务..."
        docker-compose restart
        ;;
    logs)
        echo "查看日志 (Ctrl+C 退出)..."
        docker-compose logs -f
        ;;
    logs-backend)
        echo "查看后端日志 (Ctrl+C 退出)..."
        docker-compose logs -f backend
        ;;
    logs-nginx)
        echo "查看Nginx日志 (Ctrl+C 退出)..."
        docker-compose logs -f nginx
        ;;
    status)
        echo "=== 容器状态 ==="
        docker-compose ps
        echo ""
        echo "=== 后端健康检查 ==="
        curl -s http://localhost:5000/api/version || echo "后端无响应"
        ;;
    backup)
        echo "备份数据库..."
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).db"
        cp data/reading.db "$BACKUP_FILE"
        echo "备份已保存: $BACKUP_FILE"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|logs|logs-backend|logs-nginx|status|backup}"
        exit 1
        ;;
esac
