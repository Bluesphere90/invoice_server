/**
 * PM2 Ecosystem Configuration
 * 
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 start ecosystem.config.js --env production
 *   pm2 stop all
 *   pm2 restart all
 *   pm2 logs
 */

module.exports = {
    apps: [
        {
            name: "invoice-api",
            script: "uvicorn",
            args: "backend.api.main:app --host 0.0.0.0 --port 8000",
            interpreter: "python3",
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
            script: "python3",
            args: "-m backend.collector.main",
            cwd: "/home/tran-ninh/OtherProjects/invoice_server",
            instances: 1,
            autorestart: true,
            watch: false,
            cron_restart: "0 */6 * * *",  // Restart every 6 hours
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
        }
    ]
};
