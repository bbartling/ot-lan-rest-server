# WasmFastApiExperiments

Hoping to give this a whirl to make a generic web app using the Python Fast API framework and Rust to create the front end... Yee Ha!..

```bash
/WasmFastApiExperiments
│
├── frontend/               # Front-end Rust+Wasm module
│   ├── src/                # Rust source files
│   │   └── lib.rs          # Main Rust source file for Wasm module
│   ├── Cargo.toml          # Rust package manifest
│   ├── wasm-pack-build.sh  # Shell script to run wasm-pack build
│   └── pkg/                # Generated package by wasm-pack (Wasm and JS glue code)
│
├── backend/                # Back-end FastAPI app
│   ├── app/                # FastAPI application
│   │   ├── __init__.py     # Initializes Python package
│   │   ├── main.py         # Main FastAPI app
│   │   └── dependencies.py # Optional: FastAPI dependencies (e.g., database, auth)
│   ├── requirements.txt    # Python dependencies for FastAPI app
│   └── run-server.sh       # Shell script to run UVicorn server
│
├── static/                 # Static files served by FastAPI
│   ├── index.html          # HTML file that loads the Wasm module
│   └── js/                 # Additional JavaScript files (if necessary)
│
├── tests/                  # Tests for both front-end and back-end
│   ├── frontend/           # Rust tests
│   └── backend/            # FastAPI tests
│
├── .gitignore              # Standard .gitignore file
├── README.md               # Project documentation
└── setup.md                # Setup instructions
```
