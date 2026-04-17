from fastapi import HTTPException, status

# Reusable pre-built exceptions — import these in routers
# instead of writing HTTPException everywhere

CredentialsException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

InactiveUserException = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Inactive user account",
)

NotFoundException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found",
)

ForbiddenException = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Not enough permissions",
)

DuplicateException = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Resource already exists",
)
