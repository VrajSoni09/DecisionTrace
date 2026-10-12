def extract_dependency_summary(doc: object) -> dict[str, list[str] | dict[str, int]]:
    subject_tokens: list[str] = []
    verb_tokens: list[str] = []
    dependencies: dict[str, int] = {}

    tokens = getattr(doc, "tokens", doc)
    for token in tokens:
        dep = token.dep_
        if dep:
            dependencies[dep] = dependencies.get(dep, 0) + 1
        if dep in {"nsubj", "nsubjpass", "dobj"}:
            subject_tokens.append(token.text)
        if token.pos_ == "VERB":
            verb_tokens.append(token.text)

    return {"dependencies": dependencies, "subjects": subject_tokens, "verbs": verb_tokens}
