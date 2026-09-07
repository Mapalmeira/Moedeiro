from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies.authentication import AuthenticatedUser
from app.api.dependencies.ledger import ledger_unit_of_work_factory
from app.api.ledger.schema.category import CategoryResponse, CategoryTreeNodeResponse, CreateCategoryRequest, UpdateCategoryRequest
from app.application.ledger.exceptions import CategoryDepthExceededError, CategoryInUseError, CategoryNameUnavailableError, CategoryNotFoundError, CategoryTreeSizeExceededError, InvalidCategoryHierarchyError
from app.application.ledger.use_cases.category import create_category, delete_category, get_category, get_category_tree, update_category


router = APIRouter(prefix="/api/ledgers/{ledger_uuid}/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_category(ledger_uuid: UUID, payload: CreateCategoryRequest, request: Request, user: AuthenticatedUser) -> CategoryResponse:
    try:
        category = create_category(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            payload.name,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
            payload.parent_uuid,
        )
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except CategoryTreeSizeExceededError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category limit exceeded") from error
    except CategoryNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name unavailable") from error
    except CategoryDepthExceededError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category depth limit exceeded") from error
    except InvalidCategoryHierarchyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid category hierarchy") from error
    return CategoryResponse.from_category(category)


@router.get("/tree", response_model=list[CategoryTreeNodeResponse])
def get_ledger_category_tree(ledger_uuid: UUID, request: Request, user: AuthenticatedUser) -> list[CategoryTreeNodeResponse]:
    try:
        tree = get_category_tree(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid))
    except CategoryTreeSizeExceededError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category limit exceeded") from error
    return [CategoryTreeNodeResponse.from_node(node) for node in tree]


@router.get("/{category_uuid}", response_model=CategoryResponse)
def get_ledger_category(ledger_uuid: UUID, category_uuid: UUID, request: Request, user: AuthenticatedUser) -> CategoryResponse:
    try:
        category = get_category(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), category_uuid)
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    return CategoryResponse.from_category(category)


@router.put("/{category_uuid}", response_model=CategoryResponse)
def update_ledger_category(ledger_uuid: UUID, category_uuid: UUID, payload: UpdateCategoryRequest, request: Request, user: AuthenticatedUser) -> CategoryResponse:
    try:
        category = update_category(
            ledger_unit_of_work_factory(request, user.uuid, ledger_uuid),
            category_uuid,
            payload.name,
            payload.icon,
            bytes.fromhex(payload.color_code[1:]),
            payload.parent_uuid,
        )
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except CategoryNameUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name unavailable") from error
    except CategoryDepthExceededError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category depth limit exceeded") from error
    except InvalidCategoryHierarchyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid category hierarchy") from error
    return CategoryResponse.from_category(category)


@router.delete("/{category_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ledger_category(ledger_uuid: UUID, category_uuid: UUID, request: Request, user: AuthenticatedUser) -> None:
    try:
        delete_category(ledger_unit_of_work_factory(request, user.uuid, ledger_uuid), category_uuid)
    except CategoryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found") from error
    except CategoryInUseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category is in use") from error
