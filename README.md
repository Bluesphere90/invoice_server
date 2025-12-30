invoice_server/
│
├── app/
│   ├── main.py              # entrypoint (systemd gọi)
│   ├── service.py           # khởi động scheduler + worker
│   ├── scheduler.py         # logic chạy job định kỳ
│   ├── worker.py            # xử lý 1 company
│   │
│   ├── http/
│   │   ├── __init__.py
│   │   ├── client.py        # requests.Session + retry
│   │   └── endpoints.py     # URL constants
│   │
│   ├── captcha/
│   │   ├── __init__.py
│   │   ├── solver.py        # interface solve(svg)
│   │   └── svg_solver.py    # port SVGCaptchaSolver (regex)
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py    # postgres connection
│   │   ├── models.py        # logical schema
│   │   └── repository.py    # CRUD logic
│   │
│   ├── security/
│   │   ├── crypto.py        # encrypt/decrypt password
│   │   └── secrets.py       # load key
│   │
│   ├── config/
│   │   ├── settings.py      # load env/yaml
│   │   └── defaults.yaml
│   │
│   ├── observability/
│   │   ├── logging.py       # logging config
│   │   └── alerts.py        # email/telegram (optional)
│   │
│   └── utils/
│       └── time.py
│
├── storage/
│   ├── captchas/            # SVG fail để debug
│   └── invoices/            # raw JSON (optional)
│
├── deploy/
│   ├── invoice.service      # systemd service
│   └── invoice.timer        # systemd timer
│
├── migrations/              # alembic (sau)
│
├── requirements.txt
└── README.md


