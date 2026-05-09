from fastapi import HTTPException

class LLMServiceUnavailable(HTTPException):
    def __init__(self, detail: str = "Serviço de IA indisponível"):
        super().__init__(status_code=503, detail=detail)

class DatabaseError(HTTPException):
    def __init__(self, detail: str = "Erro no banco de dados"):
        super().__init__(status_code=500, detail=detail)

class InvalidCredentials(HTTPException):
    def __init__(self, detail: str = "Credenciais inválidas"):
        super().__init__(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})

class TokenExpired(HTTPException):
    def __init__(self, detail: str = "Token expirado"):
        super().__init__(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})
