from typing import Optional

from core.di.repository_injection import get_user_repository
from database.models import Usuarios
from utils.jwt_util import JWTUtil, JWTBearer
from repositories.usuarios_repository import UsuariosRepository
from schemas.usuarios_schema import UsuariosResponse, Token
from fastapi import Depends, HTTPException, Request, status
from core.exceptions.auth_exception import InvalidCredentialsException
from utils.jwt_util import JWTUtil
from typing import Annotated
from core.settings import Settings
from utils.logger_util import LoggerUtil

log = LoggerUtil()


class AuthService:
    def __init__(self, user_repository: UsuariosRepository) -> None:
        self._user_repo = user_repository

    async def login(self, username: str, password: str) -> Optional[str]:

        # Validación para superusuario
        if username != Settings().API_USER_ADMINISTRATOR:
            user = await self._user_repo.get_by_username(username)
            if not user or not self._verify_password(password, user.clave):
                log.info(f"Credenciales inválidas para {username}!")
                raise InvalidCredentialsException("Credenciales inválidas")

            if not user.estado:
                raise HTTPException(status_code=400, detail='Usuario inactivo')

            return self.create_token(sub=user.nick_name, email=user.email, fullname=user.full_name, role=user.rol_nombre,is_active=user.estado)
        else:
            if not self._verify_password(password, Settings().API_PASSWORD_ADMINISTRATOR):
                raise InvalidCredentialsException("Credenciales inválidas para superadmin")

            return self.create_token(sub='superadmin', email='admin@metalteco.com', fullname='SysAdmin', role='SuperAdministrador', is_active=True)

    @staticmethod
    def create_token(sub: str, email: Optional[str], fullname: str, role:  Optional[str], is_active: bool) -> Optional[str]:

        try:
            token_data = {
                'sub': sub,
                'email': email,
                'fullname': fullname,
                'role': role,
                'is_active': is_active
            }
            return JWTUtil.create_token(token_data)
        except Exception as e:
            log.error(f"Error formando token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Creación de token fallida"
            )

    async def refresh_token(self, refresh_token: str) -> Optional[str]:
        try:
            payload = JWTUtil.verify_token(refresh_token)
            if not payload:
                return None  

            user = payload.get("sub")
            user = await self._user_repo.get_by_username(user)
            if not user:
                return None

            token_data = {
            'sub': user.nick_name,
            'email': user.email,
            'fullname': user.full_name,
            "role" : user.rol_nombre,
            'is_active': user.estado
            }

            return JWTUtil.create_refresh_token(token_data)
        except Exception as e:
            log.error(f"Error refreshing token: {e}")
            raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="Refrescado de token fallído"
            )
            #return None  # Handle errors gracefully


    def __verify_email(self, email: str) -> Optional[UsuariosResponse]:
        """
        Private method responsible for checking if an email exists in the database.

        Args:
            email (str): The email address to check.

        Returns:
            UserModel | None: The user instance if found, otherwise None.
        """

        user = self._user_repo.get_by_email(email)

        if user:
            return user
        return None
    
    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        from utils.any_utils import AnyUtils
        """
        Private method responsible for verifying if the provided password matches the stored password.

        Args:
            plain_password (str): The password provided in the login request.
            hashed_password (str): The hashed password stored in the database.
s
        Returns:
            bool: True if the passwords match, otherwise False.
        """
        return AnyUtils.check_password_hash(plain_password, hashed_password)

    @staticmethod
    async def get_current_user(token: Annotated[Token, Depends(JWTBearer())], user_repository: UsuariosRepository = Depends(get_user_repository)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = JWTUtil.verify_token(token)
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTUtil:
            raise

        user = await user_repository.get_by_username(username)
        if user is None:
            raise InvalidCredentialsException

        if not user.estado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo. Contacte al administrador."
            )
        return user

    async def get_current_admin_user(self: Usuarios = Depends(get_current_user)):
        if self.rol_id != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos de administrador"
            )
        return self

    async def get_current_super_user(self: Usuarios = Depends(get_current_user)) -> Usuarios:
        if not self.rol_id == 4:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough privileges"
            )
        return self