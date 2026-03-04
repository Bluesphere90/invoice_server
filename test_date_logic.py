from datetime import date, timedelta

def get_quarter_start(d: date) -> date:
    month = (d.month - 1) // 3 * 3 + 1
    return date(d.year, month, 1)

def test_logic(today_date, description):
    print(f"--- {description} ---")
    print(f"Today: {today_date} (Weekday: {today_date.weekday()})")
    
    if today_date.weekday() == 6:
        from_date = get_quarter_start(today_date)
        print(f"Run Type: SUNDAY (Quarter Start)")
    else:
        from_date = today_date - timedelta(days=30)
        print(f"Run Type: NORMAL (Last 30 Days)")
        
    print(f"From Date: {from_date}")
    print(f"To Date:   {today_date}")
    print()

# Test Case 1: A Sunday (e.g., 2026-02-08)
test_logic(date(2026, 2, 8), "Sunday in Q1 2026")

# Test Case 2: A normal day (e.g., 2026-02-09)
test_logic(date(2026, 2, 9), "Monday in Q1 2026")

# Test Case 3: Sunday at start of Q2 (e.g., 2026-04-05)
test_logic(date(2026, 4, 5), "Sunday in Q2 2026")
