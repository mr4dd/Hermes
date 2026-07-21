import shutil


def print_search_results(results: list[tuple[str, str]]) -> None:
    if not results:
        print("No results found")
        return

    terminal_width = shutil.get_terminal_size((80, 20)).columns
    description_width = max(20, terminal_width - 20)

    headers = ("#", "File", "Description")
    rows = [(index, filename, description) for index, (filename, description) in enumerate(results, start=1)]

    file_width = max(10, min(30, max(len(str(filename)) for _, filename, _ in rows)))
    column_widths = [len(header) for header in headers]
    column_widths[1] = max(column_widths[1], file_width)
    max_description_length = max(len(str(description)) for _, _, description in rows)
    column_widths[2] = max(column_widths[2], min(description_width, max_description_length))

    def wrap_text(text: str, width: int) -> list[str]:
        words = text.split()
        wrapped: list[str] = []
        current: list[str] = []
        current_length = 0

        for word in words:
            if current and current_length + len(word) + 1 > width:
                wrapped.append(" ".join(current))
                current = [word]
                current_length = len(word)
            else:
                current.append(word)
                current_length += len(word) + (0 if not current[:-1] else 1)

        if current:
            wrapped.append(" ".join(current))

        return wrapped or [""]

    def format_row(values: tuple[object, ...]) -> str:
        rendered = []
        for index, value in enumerate(values):
            if index == 2:
                rendered.append(str(value))
            else:
                rendered.append(str(value).ljust(column_widths[index]))
        return " | ".join(rendered)

    print("\nSearch Results")
    print("=" * (sum(column_widths) + 3 * (len(headers) - 1)))
    print(format_row(headers))
    print("-" * (sum(column_widths) + 3 * (len(headers) - 1)))

    for _, filename, description in rows:
        wrapped_description = wrap_text(description, column_widths[2])
        print(format_row((_, filename, wrapped_description[0])))
        for extra_line in wrapped_description[1:]:
            print("  | ".join(["".ljust(len(str(_))), "".ljust(column_widths[1]), extra_line]))

    print("=" * (sum(column_widths) + 3 * (len(headers) - 1)))
    print()
