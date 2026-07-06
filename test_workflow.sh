#!/bin/bash
git diff --name-only origin/main...HEAD > changed_files.txt

# Count different file types
total_files=$(wc -l < changed_files.txt)
source_files=$(grep -cE '\.(js|ts|jsx|tsx|py|go|rs|java|cs|cpp|c)$' changed_files.txt || echo 0)
test_files=$(grep -cE '(test|spec)\.(js|ts|jsx|tsx|py|go|rs|java|cs)$' changed_files.txt || echo 0)
doc_files=$(grep -cE '\.(md|txt|rst|adoc)$' changed_files.txt || echo 0)

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
