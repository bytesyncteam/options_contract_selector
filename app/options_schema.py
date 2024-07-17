import pydantic


class Option(pydantic.BaseModel):
    root: str
    strike: float
    stockPrice: float
    expirDate: str
    callMidIv: float
    dte: int
    callAskPrice: float
    putAskPrice: float