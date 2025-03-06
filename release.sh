#!/bin/bash
set -e

TAG="v$(date +%Y.%m.%d-%H%M%S)"
echo "The following tag will be created: $TAG"

read -p "Do you want to create and push this tag? [y/N]: " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Tag creation aborted."
    exit 0
fi

if ! git diff-index --quiet HEAD --; then
    echo "Warning: There are uncommitted changes."
    read -p "Do you still want to continue? [y/N]: " uncommitted_confirm
    if [[ "$uncommitted_confirm" != "y" && "$uncommitted_confirm" != "Y" ]]; then
        echo "Tag creation aborted."
        exit 0
    fi
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: Tag $TAG already exists. Aborting."
    exit 1
fi

git tag "$TAG"
git push origin "$TAG"

echo "Tag $TAG created and pushed successfully."