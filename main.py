from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.DEBUG)

class ReqRegister(BaseModel):
    username: str
    password: str

class Resp(BaseModel):
    res: str
    code: int

app = FastAPI()

db = {}

@app.get('/ballkeeper/')
async def hello_world():
    return {'Hello': 'World'}

@app.post('/ballkeeper/register/')
async def register(req: ReqRegister) -> Resp:
    logging.debug(f'DBG: req[{req}]')
    db[req.username] = req.password

    return {'res': 'ok', 'code': 0}

@app.get('/items/{item_id}')
async def read_item(item_id: int, q: Union[str, None] = None):
    return {'item_id': item_id, 'q': q}
