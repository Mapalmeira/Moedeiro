def validate_page(page_number: int, page_size: int, max_page_size: int) -> None:
    if page_number < 1:
        raise ValueError("page_number must be greater than or equal to 1")
    if page_size < 1:
        raise ValueError("page_size must be greater than or equal to 1")
    if page_size > max_page_size:
        raise ValueError(f"page_size must be less than or equal to {max_page_size}")
