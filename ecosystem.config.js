/**
 * PM2 Ecosystem Configuration
 * 
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 start ecosystem.config.js --env production
 *   pm2 stop all
 *   pm2 restart all
 *   pm2 logs
 * 
 * Log Rotation:
 *   Install pm2-logrotate: pm2 install pm2-logrotate
 *   Configure: pm2 set pm2-logrotate:max_size 10M
 *              pm2 set pm2-logrotate:retain 3
 *              pm2 set pm2-logrotate:compress true
 */

module.exports = {
    apps: [
        {
            name: "invoice-api",
            script: "./venv/bin/uvicorn",
            args: "backend.api.main:app --host 0.0.0.0 --port 8000",
            interpreter: "none",
            cwd: "/home/tran-ninh/OtherProjects/invoice_server",
            instances: 1,
            autorestart: true,
            watch: false,
            max_memory_restart: "500M",
            env: {
                ENV: "development",
                DEBUG: "true"
            },
            env_production: {
                ENV: "production",
                DEBUG: "false"
            },
            error_file: "./storage/logs/pm2-api-error.log",
            out_file: "./storage/logs/pm2-api-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            merge_logs: true,
            time: true
        },
        {
            name: "invoice-collector",
            script: "./venv/bin/python3",
            args: "-m backend.collector.main",
            interpreter: "none",
            cwd: "/home/tran-ninh/OtherProjects/invoice_server",
            instances: 1,
            autorestart: false,
            watch: false,
            cron_restart: "0 3,15,21 * * *",
            max_memory_restart: "300M",
            env: {
                ENV: "development"
            },
            env_production: {
                ENV: "production"
            },
            error_file: "./storage/logs/pm2-collector-error.log",
            out_file: "./storage/logs/pm2-collector-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            merge_logs: true,
            time: true
        },
        {
            name: "invoice-frontend",
            script: "python3",
            args: "-m http.server 5500",
            cwd: "/home/tran-ninh/OtherProjects/invoice_server/frontend",
            instances: 1,
            autorestart: true,
            watch: false,
            error_file: "../storage/logs/pm2-frontend-error.log",
            out_file: "../storage/logs/pm2-frontend-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            time: true
        },
        {
            name: "invoice-telegram-bot",
            script: "./venv/bin/python3",
            args: "-m backend.telegram.main",
            interpreter: "none",
            cwd: "/home/tran-ninh/OtherProjects/invoice_server",
            instances: 1,
            autorestart: true,
            watch: false,
            max_memory_restart: "200M",
            env: {
                ENV: "development"
            },
            env_production: {
                ENV: "production"
            },
            error_file: "./storage/logs/pm2-telegram-bot-error.log",
            out_file: "./storage/logs/pm2-telegram-bot-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            merge_logs: true,
            time: true
        }
    ]
};
