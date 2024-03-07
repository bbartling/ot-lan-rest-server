# WasmFastApiExperiments

Hoping to give this a whirl to make a generic web app using the Python Fast API framework and Rust to create the front end... Yee-Haw!.. Am testing on Windows but the directions are for Linux/Unix.

```bash
/WasmFastApiExperiments
│
├── frontend/                  # Front-end Rust+Wasm module
│   ├── src/                   # Rust source files
│   │   └── lib.rs             # Main Rust source file for Wasm module
│   ├── Cargo.toml             # Rust package manifest
│   ├── wasm-pack-build.sh     # Shell script to run wasm-pack build
│   └── pkg/                   # Generated package by wasm-pack (Wasm and JS glue code)
│
├── backend/                   # Back-end FastAPI app
│   ├── app/                   # FastAPI application
│   │   ├── __init__.py        # Initializes Python package
│   │   ├── main.py            # Main FastAPI app with API endpoints
│   │   ├── crud.py            # CRUD operations for database models
│   │   ├── models.py          # SQLAlchemy database models
│   │   ├── schemas.py         # Pydantic models for data validation and serialization
│   │   ├── init_db.py         # Used to create the database schema based on models.py
│   │   └── database.py        # Database session management
│   ├── requirements.txt       # Python dependencies for FastAPI app
│   └── run-server.sh          # Shell script to run UVicorn server (useful for Unix-like systems)
│
├── static/                    # Static files served by FastAPI
│   ├── index.html             # HTML file that loads the Wasm module and includes user interface
│   └── js/                    # Additional JavaScript files (if necessary)
│
├── tests/                     # Tests for both front-end and back-end
│   ├── frontend/              # Rust tests
│   └── backend/               # FastAPI tests
│
├── .gitignore                 # Standard .gitignore file
├── README.md                  # Project documentation
└── setup.md                   # Setup instructions
```

## Rust front end side
Make the WASM file with Rust with the bash commands.
1. `$ cd frontend`
2. `$ cargo install wasm-pack --force`
3. `$ wasm-pack build --target web`


After building your Wasm module, you'll need to copy the generated files from `frontend/pkg` to the `static` directory.

## Python backend side
1. `$ python -m venv venv`
2. `$ source venv/bin/activate`
3. `$ pip install fastapi uvicorn`
4. `$ cd backend`
5. `$ uvicorn app.main:app --reload`

## Test in the browser
http://127.0.0.1:8000/api/greet