#!/bin/bash
#
# Demo script to show the new install.sh functionality
#

# Source the functions from install.sh
source install.sh

echo "Demo of new install.sh functionality:"
echo "====================================="
echo ""

# Test the new helper functions
echo "1. Testing ask_with_default function:"
project_name=$(ask_with_default "Enter project name" "my-awesome-project")
echo "You entered: $project_name"
echo ""

echo "2. Testing ask_required function:"
display_name=$(ask_required "Enter display name (required)")
echo "You entered: $display_name"
echo ""

echo "3. Testing ask_yes_no function:"
if ask_yes_no "Would you like to continue?"; then
    echo "You chose YES"
else
    echo "You chose NO"
fi
echo ""

echo "Demo completed!"
