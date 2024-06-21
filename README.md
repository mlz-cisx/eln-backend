## Installation

- Ubuntu 22.04.4 
- python 3.10
- create virtual environment e.g. *venv*
- install from requirements
- create postrgres database
- enter credentials into joeseln_backend/conf/base_conf.py
- run joeseln_backend/models/table_creator.py
- enter virtual environment e.g. *source venv/bin/activate*
- because of nested async calls with websockets we need *--loop asyncio*, you can start from directory where the main.py is located with:

  ```uvicorn main:app --reload --port 8010 --host 0.0.0.0 --loop asyncio```
- see also: https://www.uvicorn.org/#command-line-options