"""
Telegram Bot Service

Interactive Telegram bot with polling-based message handler for invoice lookup
and collector control.
"""
import asyncio
import httpx
import re
from datetime import date, timedelta
from typing import Optional, Dict, Any, List, Callable

from backend.config import settings
from backend.observability.logger import get_logger
from backend.database import get_connection, close_connection, init_database
from backend.database.company_repository import CompanyRepository
from backend.database.repository import InvoiceRepository
from backend.collector.job_manager import JobManager, run_collector_job
from backend.telegram.keyboard import (
    build_company_keyboard,
    build_invoice_type_keyboard,
    build_date_range_keyboard,
    build_pagination_keyboard,
    build_collector_company_keyboard,
    build_collector_date_keyboard,
)

logger = get_logger(__name__)


class TelegramBotService:
    """
    Interactive Telegram bot with command handlers.
    
    Commands:
        /start - Welcome message and help
        /companies - List all companies
        /stats - Quick statistics
        /invoices - Interactive invoice lookup
        /hd <mst> <vao|ra> [days] - Quick invoice lookup
        /ct <number> - View invoice detail from last search
        /collect - Interactive collector trigger
        /collect <mst|all> [days] - Quick collector trigger
    """
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0
        self.running = False
        
        # Session cache for multi-step flows
        # Format: {chat_id: {"invoices": [...], "context": {...}}}
        self.session_cache: Dict[int, Dict[str, Any]] = {}
        
        # Command handlers
        self.commands: Dict[str, Callable] = {
            "start": self.cmd_start,
            "help": self.cmd_start,
            "companies": self.cmd_companies,
            "stats": self.cmd_stats,
            "invoices": self.cmd_invoices,
            "hd": self.cmd_hd,
            "ct": self.cmd_ct,
            "collect": self.cmd_collect,
        }
    
    # =========================================================================
    # HTTP Helpers
    # =========================================================================
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request to Telegram API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if method == "GET":
                    resp = await client.get(url, params=kwargs.get("params"))
                else:
                    resp = await client.post(url, json=kwargs.get("json"))
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.warning(f"Telegram API error: {resp.status_code} - {resp.text}")
                    return None
        except Exception as e:
            logger.error(f"Telegram request error: {e}")
            return None
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None,
        disable_notification: bool = False,
    ) -> Optional[Dict]:
        """Send a text message."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        return await self._request("POST", "sendMessage", json=payload)
    
    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Edit an existing message."""
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        return await self._request("POST", "editMessageText", json=payload)
    
    async def answer_callback(self, callback_query_id: str, text: str = "") -> None:
        """Answer a callback query (remove loading state)."""
        await self._request("POST", "answerCallbackQuery", json={
            "callback_query_id": callback_query_id,
            "text": text,
        })
    
    async def send_document(
        self,
        chat_id: int,
        document: bytes,
        filename: str,
        caption: str = "",
    ) -> Optional[Dict]:
        """Send a document (for Excel export)."""
        url = f"{self.base_url}/sendDocument"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                files = {"document": (filename, document)}
                data = {"chat_id": chat_id, "caption": caption}
                resp = await client.post(url, files=files, data=data)
                return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"Send document error: {e}")
            return None
    
    # =========================================================================
    # Polling
    # =========================================================================
    
    async def start_polling(self):
        """Main polling loop."""
        self.running = True
        logger.info("Telegram Bot started polling...")
        
        while self.running:
            try:
                result = await self._request("GET", "getUpdates", params={
                    "offset": self.offset,
                    "timeout": 30,
                    "allowed_updates": ["message", "callback_query"]
                })
                
                if result and result.get("ok") and result.get("result"):
                    for update in result["result"]:
                        self.offset = update["update_id"] + 1
                        await self.handle_update(update)
                        
            except asyncio.CancelledError:
                logger.info("Polling cancelled")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop polling."""
        self.running = False
    
    # =========================================================================
    # Update Handler
    # =========================================================================
    
    async def handle_update(self, update: Dict) -> None:
        """Route update to appropriate handler."""
        try:
            if "callback_query" in update:
                await self.handle_callback(update["callback_query"])
            elif "message" in update and "text" in update["message"]:
                await self.handle_message(update["message"])
        except Exception as e:
            logger.exception(f"Error handling update: {e}")
    
    async def handle_message(self, message: Dict) -> None:
        """Handle incoming text message."""
        chat_id = message["chat"]["id"]
        text = message["text"].strip()
        
        # Check authorization (only respond to configured chat_id)
        if str(chat_id) != str(self.chat_id):
            logger.warning(f"Unauthorized chat_id: {chat_id}")
            await self.send_message(chat_id, "⛔ Bạn không có quyền sử dụng bot này.")
            return
        
        # Parse command
        if text.startswith("/"):
            parts = text[1:].split()
            cmd = parts[0].lower().split("@")[0]  # Remove @botname suffix
            args = parts[1:]
            
            if cmd in self.commands:
                await self.commands[cmd](chat_id, args)
            else:
                await self.send_message(chat_id, f"❓ Không hiểu lệnh /{cmd}. Gõ /start để xem hướng dẫn.")
    
    async def handle_callback(self, callback: Dict) -> None:
        """Handle inline keyboard callback."""
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data = callback["data"]
        
        # Answer callback to remove loading state
        await self.answer_callback(callback["id"])
        
        # Route by prefix
        if data == "noop":
            return
        elif data.startswith("company:"):
            await self.cb_company_selected(chat_id, message_id, data)
        elif data.startswith("type:"):
            await self.cb_type_selected(chat_id, message_id, data)
        elif data.startswith("range:"):
            await self.cb_range_selected(chat_id, message_id, data)
        elif data.startswith("page:"):
            await self.cb_page_selected(chat_id, message_id, data)
        elif data.startswith("collect_co:"):
            await self.cb_collect_company(chat_id, message_id, data)
        elif data.startswith("collect_run:"):
            await self.cb_collect_run(chat_id, message_id, data)
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    async def cmd_start(self, chat_id: int, args: List[str]) -> None:
        """Show welcome and help message."""
        text = """
🤖 <b>Invoice Bot</b>

Các lệnh có sẵn:

<b>📄 Tra cứu hóa đơn</b>
/invoices - Tra cứu qua menu
/hd &lt;mst&gt; &lt;vao|ra&gt; [ngày] - Tra nhanh
/ct &lt;số&gt; - Xem chi tiết

<b>🚀 Thu thập hóa đơn</b>
/collect - Thu thập qua menu
/collect &lt;mst|all&gt; [ngày] - Thu nhanh

<b>📊 Khác</b>
/companies - Danh sách công ty
/stats - Thống kê nhanh

<b>Ví dụ:</b>
<code>/hd 0311721886 vao 30</code>
<code>/collect all 7</code>
        """.strip()
        await self.send_message(chat_id, text)
    
    async def cmd_companies(self, chat_id: int, args: List[str]) -> None:
        """List all companies."""
        try:
            init_database()
            conn = get_connection()
            repo = CompanyRepository(conn)
            companies = repo.get_all_companies()
            
            if not companies:
                await self.send_message(chat_id, "📭 Chưa có công ty nào được thêm.")
                return
            
            lines = ["🏢 <b>Danh sách công ty</b>\n"]
            for i, c in enumerate(companies, 1):
                status = "✅" if c.get("is_active", True) else "❌"
                name = c.get("company_name") or "Chưa có tên"
                lines.append(f"{i}. {status} <b>{c['tax_code']}</b>\n   {name}")
            
            await self.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            logger.exception(f"cmd_companies error: {e}")
            await self.send_message(chat_id, f"❌ Lỗi: {e}")
        finally:
            close_connection()
    
    async def cmd_stats(self, chat_id: int, args: List[str]) -> None:
        """Show quick statistics."""
        try:
            init_database()
            conn = get_connection()
            
            with conn.cursor() as cur:
                # Total invoices
                cur.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(tgtttbso), 0) as total FROM invoices")
                row = cur.fetchone()
                total_inv = row["cnt"]
                total_value = float(row["total"]) if row["total"] else 0
                
                # Companies count
                cur.execute("SELECT COUNT(*) as cnt FROM companies WHERE is_active = TRUE")
                total_companies = cur.fetchone()["cnt"]
                
                # Invoices today
                today = date.today().isoformat()
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM invoices WHERE tdlap >= %s",
                    (today,)
                )
                today_inv = cur.fetchone()["cnt"]
            
            text = f"""
📊 <b>Thống kê nhanh</b>

🏢 Công ty đang hoạt động: <b>{total_companies}</b>
📄 Tổng số hóa đơn: <b>{total_inv:,}</b>
📅 Hóa đơn hôm nay: <b>{today_inv}</b>
💰 Tổng giá trị: <b>{total_value:,.0f} VND</b>
            """.strip()
            
            await self.send_message(chat_id, text)
        except Exception as e:
            logger.exception(f"cmd_stats error: {e}")
            await self.send_message(chat_id, f"❌ Lỗi: {e}")
        finally:
            close_connection()
    
    async def cmd_invoices(self, chat_id: int, args: List[str]) -> None:
        """Interactive invoice lookup - step 1: select company."""
        try:
            init_database()
            conn = get_connection()
            repo = CompanyRepository(conn)
            companies = repo.get_active_companies()
            
            if not companies:
                await self.send_message(chat_id, "📭 Chưa có công ty nào.")
                return
            
            keyboard = build_company_keyboard(companies, prefix="company")
            await self.send_message(
                chat_id,
                "📄 <b>Tra cứu hóa đơn</b>\n\nChọn công ty:",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.exception(f"cmd_invoices error: {e}")
            await self.send_message(chat_id, f"❌ Lỗi: {e}")
        finally:
            close_connection()
    
    async def cmd_hd(self, chat_id: int, args: List[str]) -> None:
        """Quick invoice lookup: /hd <mst> <vao|ra> [days]"""
        if len(args) < 2:
            await self.send_message(
                chat_id,
                "❓ <b>Cách dùng:</b>\n<code>/hd &lt;mst&gt; &lt;vao|ra&gt; [ngày]</code>\n\n"
                "<b>Ví dụ:</b>\n<code>/hd 0311721886 vao 30</code>"
            )
            return
        
        tax_code = args[0]
        inv_type = args[1].lower()
        days = int(args[2]) if len(args) > 2 else 7
        
        if inv_type not in ("vao", "ra", "in", "out"):
            await self.send_message(chat_id, "❌ Loại hóa đơn phải là 'vao' hoặc 'ra'")
            return
        
        # Map to database query
        is_purchase = inv_type in ("vao", "in")
        
        await self._search_invoices(chat_id, tax_code, is_purchase, days)
    
    async def cmd_ct(self, chat_id: int, args: List[str]) -> None:
        """View invoice detail from last search."""
        if not args:
            await self.send_message(chat_id, "❓ Cách dùng: <code>/ct &lt;số&gt;</code>")
            return
        
        try:
            idx = int(args[0]) - 1
        except ValueError:
            await self.send_message(chat_id, "❌ Số không hợp lệ")
            return
        
        # Get from session cache
        session = self.session_cache.get(chat_id, {})
        invoices = session.get("invoices", [])
        
        if not invoices:
            await self.send_message(chat_id, "📭 Chưa có kết quả tra cứu. Hãy dùng /hd hoặc /invoices trước.")
            return
        
        if idx < 0 or idx >= len(invoices):
            await self.send_message(chat_id, f"❌ Số phải từ 1 đến {len(invoices)}")
            return
        
        inv = invoices[idx]
        await self._show_invoice_detail(chat_id, inv["id"])
    
    async def cmd_collect(self, chat_id: int, args: List[str]) -> None:
        """Collector trigger."""
        if args:
            # Quick mode: /collect <mst|all> [days]
            tax_code = args[0]
            days = int(args[1]) if len(args) > 1 else 7
            await self._run_collector(chat_id, tax_code, days)
        else:
            # Interactive mode
            try:
                init_database()
                conn = get_connection()
                repo = CompanyRepository(conn)
                companies = repo.get_active_companies()
                
                if not companies:
                    await self.send_message(chat_id, "📭 Chưa có công ty nào.")
                    return
                
                keyboard = build_collector_company_keyboard(companies)
                await self.send_message(
                    chat_id,
                    "🚀 <b>Thu thập hóa đơn</b>\n\nChọn công ty:",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.exception(f"cmd_collect error: {e}")
                await self.send_message(chat_id, f"❌ Lỗi: {e}")
            finally:
                close_connection()
    
    # =========================================================================
    # Callback Handlers
    # =========================================================================
    
    async def cb_company_selected(self, chat_id: int, message_id: int, data: str) -> None:
        """Handle company selection for invoice lookup."""
        _, tax_code = data.split(":", 1)
        
        keyboard = build_invoice_type_keyboard(tax_code)
        await self.edit_message(
            chat_id, message_id,
            f"🏢 <b>MST: {tax_code}</b>\n\nChọn loại hóa đơn:",
            reply_markup=keyboard
        )
    
    async def cb_type_selected(self, chat_id: int, message_id: int, data: str) -> None:
        """Handle invoice type selection."""
        _, tax_code, inv_type = data.split(":")
        
        keyboard = build_date_range_keyboard(tax_code, inv_type)
        type_text = "Vào (Mua)" if inv_type == "in" else "Ra (Bán)"
        await self.edit_message(
            chat_id, message_id,
            f"🏢 MST: {tax_code}\n📥 Loại: {type_text}\n\nChọn khoảng thời gian:",
            reply_markup=keyboard
        )
    
    async def cb_range_selected(self, chat_id: int, message_id: int, data: str) -> None:
        """Handle date range selection - perform search."""
        _, tax_code, inv_type, range_str = data.split(":")
        
        # Calculate days
        if range_str == "month":
            today = date.today()
            days = today.day
        elif range_str == "last_month":
            today = date.today()
            first_of_month = today.replace(day=1)
            last_month_end = first_of_month - timedelta(days=1)
            days = last_month_end.day + today.day
        else:
            days = int(range_str)
        
        is_purchase = inv_type == "in"
        
        # Delete the keyboard message first
        await self.edit_message(chat_id, message_id, "⏳ Đang tìm kiếm...")
        
        # Perform search
        await self._search_invoices(chat_id, tax_code, is_purchase, days)
    
    async def cb_page_selected(self, chat_id: int, message_id: int, data: str) -> None:
        """Handle pagination."""
        # Implementation for pagination if needed
        pass
    
    async def cb_collect_company(self, chat_id: int, message_id: int, data: str) -> None:
        """Handle collector company selection."""
        _, tax_code = data.split(":", 1)
        
        keyboard = build_collector_date_keyboard(tax_code)
        
        if tax_code == "all":
            text = "🔄 <b>Tất cả công ty</b>\n\nChọn khoảng thời gian:"
        else:
            text = f"🏢 <b>MST: {tax_code}</b>\n\nChọn khoảng thời gian:"
        
        await self.edit_message(chat_id, message_id, text, reply_markup=keyboard)
    
    async def cb_collect_run(self, chat_id: int, message_id: int, data: str) -> None:
        """Handle collector execution."""
        _, tax_code, range_str = data.split(":")
        
        if range_str == "month":
            days = date.today().day
        else:
            days = int(range_str)
        
        await self.edit_message(chat_id, message_id, "⏳ Đang bắt đầu thu thập...")
        await self._run_collector(chat_id, tax_code, days)
    
    # =========================================================================
    # Business Logic
    # =========================================================================
    
    async def _search_invoices(
        self, chat_id: int, tax_code: str, is_purchase: bool, days: int
    ) -> None:
        """Search invoices and send results."""
        try:
            init_database()
            conn = get_connection()
            
            to_date = date.today()
            from_date = to_date - timedelta(days=days)
            
            # Build query based on invoice type
            if is_purchase:
                # Purchase invoices: buyer is tax_code
                condition = "nmmst = %s"
            else:
                # Sold invoices: seller is tax_code  
                condition = "nbmst = %s"
            
            sql = f"""
                SELECT id, nbmst, nbten, nmmst, nmten, shdon, khhdon, tdlap,
                       tgtcthue, tgtthue, tgtttbso
                FROM invoices
                WHERE {condition}
                  AND tdlap >= %s AND tdlap <= %s
                ORDER BY tdlap DESC, shdon DESC
                LIMIT 30
            """
            
            
            with conn.cursor() as cur:
                # First check count
                count_sql = f"SELECT COUNT(*) as cnt FROM invoices WHERE {condition} AND tdlap >= %s AND tdlap <= %s"
                cur.execute(count_sql, (tax_code, from_date.isoformat(), to_date.isoformat() + "T23:59:59"))
                total_count = cur.fetchone()["cnt"]
                
                if total_count > 30:
                    await self.send_message(
                        chat_id,
                        f"⚠️ <b>Tìm thấy {total_count} hóa đơn</b>\n\n"
                        f"Số lượng quá lớn để hiển thị. Vui lòng chọn khoảng thời gian ngắn hơn."
                    )
                    return

                cur.execute(sql, (tax_code, from_date.isoformat(), to_date.isoformat() + "T23:59:59"))
                rows = cur.fetchall()
            
            invoices = [dict(r) for r in rows] if rows else []
            
            # Cache for /ct command
            self.session_cache[chat_id] = {
                "invoices": invoices,
                "context": {
                    "tax_code": tax_code,
                    "is_purchase": is_purchase,
                    "days": days,
                }
            }
            
            if not invoices:
                type_text = "Vào" if is_purchase else "Ra"
                await self.send_message(
                    chat_id,
                    f"📭 Không tìm thấy hóa đơn {type_text} cho MST {tax_code} trong {days} ngày qua."
                )
                return
            
            # Format results
            type_emoji = "📥" if is_purchase else "📤"
            type_text = "Vào" if is_purchase else "Ra"
            
            lines = [f"{type_emoji} <b>HĐ {type_text} - {tax_code}</b> ({days} ngày)\n"]
            
            for i, inv in enumerate(invoices[:30], 1):
                tdlap = inv.get("tdlap", "")[:10] if inv.get("tdlap") else "N/A"
                shdon = inv.get("shdon", "N/A")
                
                # Show counterparty - FULL NAME
                if is_purchase:
                    party = inv.get("nbten", "") or inv.get("nbmst", "N/A")
                else:
                    party = inv.get("nmten", "") or inv.get("nmmst", "N/A")
                
                total = float(inv.get("tgtttbso") or 0)
                total_str = self._format_money(total)
                
                lines.append(f"<b>#{i}</b> {tdlap} | {shdon} | {party} | {total_str}")
            
            lines.append("\n→ <code>/ct &lt;số&gt;</code> để xem chi tiết")
            
            await self.send_message(chat_id, "\n".join(lines))
            
        except Exception as e:
            logger.exception(f"_search_invoices error: {e}")
            await self.send_message(chat_id, f"❌ Lỗi: {e}")
        finally:
            close_connection()
    
    async def _show_invoice_detail(self, chat_id: int, invoice_id: str) -> None:
        """Show invoice detail."""
        try:
            init_database()
            conn = get_connection()
            
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, nbmst, nbten, nmmst, nmten, shdon, khhdon, khmshdon,
                           tdlap, nky, tgtcthue, tgtthue, tgtttbso, tthai, dvtte
                    FROM invoices WHERE id = %s
                """, (invoice_id,))
                row = cur.fetchone()
            
            if not row:
                await self.send_message(chat_id, "❌ Không tìm thấy hóa đơn")
                return
            
            inv = dict(row)
            
            # Status mapping
            tthai_map = {
                1: "Hóa đơn mới",
                2: "Thay thế",
                3: "Điều chỉnh",
                4: "Bị thay thế",
                5: "Bị điều chỉnh",
                6: "Bị hủy",
            }
            
            tdlap = inv.get("tdlap", "")[:10] if inv.get("tdlap") else "N/A"
            nky = inv.get("nky", "")[:10] if inv.get("nky") else "N/A"
            tthai = tthai_map.get(inv.get("tthai"), str(inv.get("tthai", "")))
            
            text = f"""
📄 <b>Chi tiết hóa đơn</b>
━━━━━━━━━━━━━━━

📅 Ngày lập: {tdlap}
🔢 Số: <b>{inv.get('shdon', 'N/A')}</b> | {inv.get('khhdon', '')}
🏷️ Trạng thái: {tthai}

<b>🏢 Người bán:</b>
{inv.get('nbten', 'N/A')}
MST: {inv.get('nbmst', 'N/A')}

<b>👤 Người mua:</b>
{inv.get('nmten', 'N/A')}
MST: {inv.get('nmmst', 'N/A')}

<b>💰 Giá trị:</b>
Chưa thuế: {self._format_money(inv.get('tgtcthue'))}
Thuế: {self._format_money(inv.get('tgtthue'))}
<b>Tổng: {self._format_money(inv.get('tgtttbso'))}</b>
            """.strip()
            
            await self.send_message(chat_id, text)
            
        except Exception as e:
            logger.exception(f"_show_invoice_detail error: {e}")
            await self.send_message(chat_id, f"❌ Lỗi: {e}")
        finally:
            close_connection()
    
    async def _run_collector(self, chat_id: int, tax_code: str, days: int) -> None:
        """Run collector job."""
        try:
            init_database()
            conn = get_connection()
            repo = CompanyRepository(conn)
            manager = JobManager()
            
            to_date = date.today()
            from_date = to_date - timedelta(days=days)
            
            if tax_code == "all":
                companies = repo.get_active_companies()
                if not companies:
                    await self.send_message(chat_id, "📭 Không có công ty nào.")
                    return
                
                # Start jobs for all companies
                jobs = []
                for company in companies:
                    tc = company["tax_code"]
                    
                    if manager.is_running_for(tc):
                        continue
                    
                    job = manager.create_job(tc, from_date, to_date)
                    company_with_pw = repo.get_company_with_password(tc)
                    
                    # Run in background thread
                    import threading
                    thread = threading.Thread(
                        target=run_collector_job,
                        args=(job.job_id, company_with_pw, from_date, to_date),
                        daemon=True
                    )
                    thread.start()
                    jobs.append(tc)
                
                await self.send_message(
                    chat_id,
                    f"🚀 <b>Đã bắt đầu thu thập</b>\n\n"
                    f"📅 Từ: {from_date}\n"
                    f"📅 Đến: {to_date}\n"
                    f"🏢 Công ty: {len(jobs)}\n\n"
                    f"Kết quả sẽ được gửi qua thông báo."
                )
            else:
                # Single company
                company = repo.get_company_with_password(tax_code)
                if not company:
                    await self.send_message(chat_id, f"❌ Không tìm thấy công ty MST {tax_code}")
                    return
                
                if manager.is_running_for(tax_code):
                    await self.send_message(chat_id, f"⏳ Công ty {tax_code} đang có job chạy.")
                    return
                
                job = manager.create_job(tax_code, from_date, to_date)
                
                import threading
                thread = threading.Thread(
                    target=run_collector_job,
                    args=(job.job_id, company, from_date, to_date),
                    daemon=True
                )
                thread.start()
                
                await self.send_message(
                    chat_id,
                    f"🚀 <b>Đã bắt đầu thu thập</b>\n\n"
                    f"🏢 Công ty: {company.get('company_name', tax_code)}\n"
                    f"📅 Từ: {from_date}\n"
                    f"📅 Đến: {to_date}\n\n"
                    f"Kết quả sẽ được gửi qua thông báo."
                )
                
        except Exception as e:
            logger.exception(f"_run_collector error: {e}")
            await self.send_message(chat_id, f"❌ Lỗi: {e}")
        finally:
            close_connection()
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def _format_money(self, value) -> str:
        """Format money value."""
        if value is None:
            return "0"
        try:
            v = float(value)
            if v >= 1_000_000_000:
                return f"{v/1_000_000_000:.1f} tỷ"
            elif v >= 1_000_000:
                return f"{v/1_000_000:.1f} tr"
            else:
                return f"{v:,.0f}"
        except:
            return str(value)
