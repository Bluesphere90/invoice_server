"""
Telegram Notification Service

Gửi thông báo qua Telegram Bot API để quản lý server từ xa.
"""
import httpx
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.config import settings
from backend.observability.logger import get_logger

logger = get_logger(__name__)


class TelegramNotifier:
    """
    Telegram notification service for Invoice Server.
    
    Features:
    - Send text/HTML messages
    - Collector job results
    - Error alerts
    - Server status updates
    
    Usage:
        notifier = TelegramNotifier()
        notifier.send_message("Hello from server!")
    """
    
    _instance: Optional['TelegramNotifier'] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = settings.TELEGRAM_ENABLED
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._initialized = True
        
        if not self.enabled:
            logger.info("Telegram notifications disabled")
        elif not self.bot_token or not self.chat_id:
            logger.warning("Telegram BOT_TOKEN or CHAT_ID not configured")
            self.enabled = False
    
    def _format_timestamp(self) -> str:
        """Format current timestamp in Vietnamese timezone."""
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    def send_message(
        self, 
        text: str, 
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a text message to Telegram.
        
        Args:
            text: Message content (supports HTML tags if parse_mode="HTML")
            parse_mode: "HTML" or "Markdown"
            disable_notification: If True, send silently
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            logger.debug("Telegram disabled, skipping message")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(url, json=payload)
                    
                if response.status_code == 200:
                    logger.debug("Telegram message sent successfully")
                    return True
                else:
                    logger.warning(
                        f"Telegram API error: {response.status_code} - {response.text}"
                    )
                    
            except httpx.TimeoutException:
                logger.warning(f"Telegram timeout (attempt {attempt + 1}/{max_retries})")
            except httpx.RequestError as e:
                logger.warning(f"Telegram request error: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        
        logger.error("Failed to send Telegram message after retries")
        return False
    
    # ============================================================
    # HIGH-LEVEL NOTIFICATION METHODS
    # ============================================================
    
    def send_startup_notification(self, service_name: str = "Invoice Server"):
        """Notify when server starts up."""
        message = f"""
🚀 <b>Server Started</b>

📦 Service: {service_name}
🕐 Time: {self._format_timestamp()}
🌐 Environment: {settings.ENV}
        """.strip()
        
        return self.send_message(message)
    
    def send_shutdown_notification(self, service_name: str = "Invoice Server"):
        """Notify when server shuts down."""
        message = f"""
⏹️ <b>Server Stopped</b>

📦 Service: {service_name}
🕐 Time: {self._format_timestamp()}
        """.strip()
        
        return self.send_message(message)
    
    def send_collector_started(self, companies_count: int):
        """Notify when collector job starts."""
        message = f"""
⏳ <b>Collector Started</b>

🏢 Companies: {companies_count}
🕐 Time: {self._format_timestamp()}
        """.strip()
        
        return self.send_message(message, disable_notification=True)
    
    from datetime import date
    def send_collector_result(
        self,
        company_results: List[Dict],
        duration_seconds: float,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ):
        """
        Send detailed collector run summary with per-company breakdown.
        
        Args:
            company_results: List of result dicts from collect_for_company()
                Each contains: tax_code, login_success, invoices_detected,
                invoices_downloaded, download_failed, error, error_details, company_name
            duration_seconds: How long the collector ran
            from_date: Start date of collection
            to_date: End date of collection
        """
        duration_str = self._format_duration(duration_seconds)
        
        # Calculate aggregates
        total_companies = len(company_results)
        login_success = sum(1 for r in company_results if r.get("login_success", False))
        login_failed = total_companies - login_success
        total_detected = sum(r.get("invoices_detected", 0) for r in company_results)
        total_downloaded = sum(r.get("invoices_downloaded", 0) for r in company_results)
        total_failed = sum(r.get("download_failed", 0) for r in company_results)
        
        # Determine status
        has_errors = login_failed > 0 or total_failed > 0
        status_emoji = "✅" if not has_errors else "⚠️"
        status_text = "Thành công" if not has_errors else "Có lỗi"

        # Format date range
        date_range_str = ""
        if from_date and to_date:
            f_str = from_date.strftime("%d/%m")
            t_str = to_date.strftime("%d/%m")
            date_range_str = f"📅 <b>{f_str} - {t_str}</b>\n"
        
        # Build per-company detail lines
        company_lines = []
        for r in company_results:
            tax_code = r.get("tax_code", "N/A")
            company_name = r.get("company_name", "")
            
            # Format display name: "Company Name (MST)" or just "MST"
            if company_name and company_name != tax_code:
                display_name = f"{company_name} ({tax_code})"
            else:
                display_name = tax_code

            login_ok = r.get("login_success", False)
            detected = r.get("invoices_detected", 0)
            downloaded = r.get("invoices_downloaded", 0)
            
            login_icon = "✅" if login_ok else "❌"
            
            if login_ok:
                if detected == downloaded:
                    line = f"• {display_name}: {login_icon} | {detected} phát hiện, {downloaded} tải"
                else:
                    line = f"• {display_name}: {login_icon} | {detected} phát hiện, {downloaded} tải ⚠️"
            else:
                error_short = (r.get("error", "Lỗi") or "Lỗi không xác định")[:40]
                line = f"• {display_name}: {login_icon} | {error_short}"
            
            company_lines.append(line)
        
        companies_detail = "\n".join(company_lines)
        
        message = f"""
📊 <b>Collector Report</b>

{status_emoji} Status: {status_text}
{date_range_str}
⏱️ Duration: {duration_str}
🕐 Time: {self._format_timestamp()}

📋 <b>Chi tiết theo MST:</b>
{companies_detail}

📈 <b>Tổng kết:</b>
• Companies: {total_companies} ({login_success} OK, {login_failed} lỗi)
• Invoices: {total_detected} phát hiện, {total_downloaded} tải về
        """.strip()
        
        # Add error details if any
        all_errors = []
        for r in company_results:
            if r.get("error"):
                all_errors.append(f"• {r['tax_code']}: {r['error'][:60]}")
            for detail in r.get("error_details", []):
                all_errors.append(f"  └ {detail}")
        
        if all_errors:
            error_section = "\n".join(all_errors[:10])  # Limit to 10 lines
            message += f"\n\n❌ <b>Lỗi chi tiết:</b>\n{error_section}"
            if len(all_errors) > 10:
                message += f"\n... và {len(all_errors) - 10} lỗi khác"
        
        return self.send_message(message)
    
    def send_job_completed(
        self,
        job_id: str,
        tax_code: str,
        invoices_found: int,
        invoices_processed: int,
        duration_seconds: float
    ):
        """Notify when a manual collector job completes."""
        duration_str = self._format_duration(duration_seconds)
        
        message = f"""
✅ <b>Job Completed</b>

🆔 Job: <code>{job_id}</code>
🏢 Company: {tax_code}
📄 Invoices: {invoices_found} tìm thấy, {invoices_processed} xử lý
⏱️ Duration: {duration_str}
        """.strip()
        
        return self.send_message(message)
    
    def send_job_failed(
        self,
        job_id: str,
        tax_code: str,
        error: str
    ):
        """Notify when a manual collector job fails."""
        message = f"""
❌ <b>Job Failed</b>

🆔 Job: <code>{job_id}</code>
🏢 Company: {tax_code}
⚠️ Error: {error[:200]}
🕐 Time: {self._format_timestamp()}
        """.strip()
        
        return self.send_message(message)
    
    def send_error_alert(
        self,
        error_type: str,
        message_text: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Send critical error alert.
        
        Args:
            error_type: Type/category of error
            message_text: Error message
            context: Additional context dict
        """
        message = f"""
🚨 <b>Error Alert</b>

📛 Type: {error_type}
⚠️ Message: {message_text[:300]}
🕐 Time: {self._format_timestamp()}
        """.strip()
        
        if context:
            context_lines = [f"• {k}: {v}" for k, v in list(context.items())[:5]]
            message += "\n\n📋 <b>Context:</b>\n" + "\n".join(context_lines)
        
        return self.send_message(message)
    
    def send_database_error(self, error: str):
        """Alert on database connection issues."""
        return self.send_error_alert(
            error_type="Database Error",
            message_text=error
        )
    
    def send_login_failed(self, tax_code: str, error: str):
        """Alert when login to tax portal fails."""
        return self.send_error_alert(
            error_type="Login Failed",
            message_text=error,
            context={"tax_code": tax_code}
        )
    
    def send_rate_limit_alert(self, tax_code: str, endpoint: str):
        """Alert when hitting rate limits on tax portal."""
        message = f"""
⏱️ <b>Rate Limit Hit</b>

🏢 Company: {tax_code}
🔗 Endpoint: {endpoint}
💡 Suggestion: Tăng delay giữa các requests
🕐 Time: {self._format_timestamp()}
        """.strip()
        
        return self.send_message(message)
    
    def send_daily_summary(
        self,
        total_companies: int,
        total_invoices_today: int,
        total_errors_today: int,
        disk_usage_percent: Optional[float] = None
    ):
        """Send daily status summary."""
        disk_info = f"\n💾 Disk: {disk_usage_percent:.1f}%" if disk_usage_percent else ""
        
        status_emoji = "✅" if total_errors_today == 0 else "⚠️"
        
        message = f"""
📅 <b>Daily Summary</b>

{status_emoji} Status: {'Healthy' if total_errors_today == 0 else 'Needs attention'}
🏢 Active Companies: {total_companies}
📄 Invoices Today: {total_invoices_today}
❌ Errors Today: {total_errors_today}{disk_info}
🕐 Report time: {self._format_timestamp()}
        """.strip()
        
        return self.send_message(message)
    
    def send_backup_notification(
        self,
        success: bool,
        backup_file: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Notify about backup status."""
        if success:
            message = f"""
💾 <b>Backup Completed</b>

✅ Status: Success
📁 File: {backup_file or 'N/A'}
🕐 Time: {self._format_timestamp()}
            """.strip()
        else:
            message = f"""
💾 <b>Backup Failed</b>

❌ Status: Failed
⚠️ Error: {error or 'Unknown error'}
🕐 Time: {self._format_timestamp()}
            """.strip()
        
        return self.send_message(message)
    
    def send_high_memory_alert(self, memory_percent: float, service: str):
        """Alert when memory usage is high."""
        message = f"""
🔴 <b>High Memory Usage</b>

📦 Service: {service}
💾 Memory: {memory_percent:.1f}%
💡 Action: Consider restarting service
🕐 Time: {self._format_timestamp()}
        """.strip()
        
        return self.send_message(message)
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f} giây"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} phút"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} giờ"


# Convenience function for quick alerts
def send_telegram_alert(message: str) -> bool:
    """Quick way to send a Telegram alert."""
    notifier = TelegramNotifier()
    return notifier.send_message(message)
