#!/bin/bash
git diff --name-only origin/main...HEAD > changed_files.txt

# Count different file types (using grep -E with wc -l for cross-platform compatibility)
total_files=$(wc -l < changed_files.txt)
source_files=$(grep -E '\.(js|ts|jsx|tsx|py|go|rs|java|cs|cpp|c)$' changed_files.txt | wc -l)
test_files=$(grep -E '(test|spec)\.(js|ts|jsx|tsx|py|go|rs|java|cs)$' changed_files.txt | wc -l)
doc_files=$(grep -E '\.(md|txt|rst|adoc)$' changed_files.txt | wc -l)

echo "total_files=$total_files"
echo "source_files=$source_files"
echo "test_files=$test_files"
echo "doc_files=$doc_files"

# Check if tests were added for source changes
if [ "$source_files" -gt 0 ] && [ "$test_files" -eq 0 ]; then
  echo "needs_tests=true"
else
  echo "needs_tests=false"
fi

# Check PR size
if [ "$total_files" -gt 50 ]; then
  echo "size=large"
elif [ "$total_files" -gt 20 ]; then
  echo "size=medium"
else
  echo "size=small"
fi
