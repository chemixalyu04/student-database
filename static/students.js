// app.js

// Function to confirm deletion
function confirmDelete() {
  const confirmButton = document.getElementById("confirmDelete");
  const deleteButton = document.querySelector(".delete-button"); // Adjust to your delete button's class

  // Show the confirmation modal on delete button click
  deleteButton.addEventListener("click", function () {
    $("#confirmationModal").modal("show"); // Show the modal
  });

  // Proceed with deletion when confirm button is clicked
  confirmButton.addEventListener("click", function () {
    // Add the logic to delete the student here
    // Example: Make an AJAX call to delete the student
    console.log("Student deleted"); // Placeholder action
  });
}

// Show loading spinner on form submission
document.addEventListener("submit", function () {
  document.getElementById("loading").style.display = "block"; // Show loading spinner
});

// Initialize the confirm delete function
confirmDelete();
