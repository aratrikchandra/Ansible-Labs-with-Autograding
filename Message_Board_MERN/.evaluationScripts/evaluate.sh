#! /bin/bash

INSTRUCTOR_SCRIPTS="/home/.evaluationScripts"
LAB_DIRECTORY="../labDirectory"
ptcd=$(pwd)

cd "$INSTRUCTOR_SCRIPTS"

# Get a list of existing files in autograder *before copying*
cd autograder/
find . -mindepth 1 > ../existing_files.txt
cd ..

# Copy labDirectory contents except the 'inventory' folder
rsync -av --exclude='inventory' "$LAB_DIRECTORY"/ autograder/

# Determine which files were newly copied into autograder
cd autograder/
find . -mindepth 1 > ../all_files_after.txt
cd ..
grep -Fxv -f existing_files.txt all_files_after.txt > to_delete.txt

# Fix permissions for all files (including newly copied ones)
cd autograder/
chmod -R 777 *
cd ..

# Run the grading script
cd autograder/
./grader.sh
cd ..

# Delete ONLY the copied files (not pre-existing ones)
cd autograder/
xargs -d '\n' rm -rf < ../to_delete.txt
cd ..

# Cleanup temporary files
rm existing_files.txt all_files_after.txt to_delete.txt

cd "$ptcd"