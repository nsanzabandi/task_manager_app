// project_form.js - Dynamic admin filtering based on division selection

document.addEventListener('DOMContentLoaded', function() {
    const divisionSelect = document.getElementById('id_division');
    const adminSelect = document.getElementById('id_assigned_to_admin');
    
    if (!divisionSelect || !adminSelect) {
        return; // Elements not found
    }

    // Function to update admin options based on selected division
    function updateAdminOptions() {
        const divisionId = divisionSelect.value;
        
        if (!divisionId) {
            // Clear admin select and show placeholder
            adminSelect.innerHTML = '<option value="">Select Admin (choose division first)</option>';
            adminSelect.disabled = true;
            return;
        }

        // Show loading state
        adminSelect.innerHTML = '<option value="">Loading admins...</option>';
        adminSelect.disabled = true;

        // Fetch admins for the selected division
        fetch(`/ajax/get-division-admins/?division_id=${divisionId}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }

            // Clear existing options
            adminSelect.innerHTML = '<option value="">Select Admin</option>';
            
            // Add admin options
            data.admins.forEach(admin => {
                const option = document.createElement('option');
                option.value = admin.id;
                option.textContent = admin.name;
                adminSelect.appendChild(option);
            });

            // Enable the select
            adminSelect.disabled = false;

            // If no admins found, show message
            if (data.admins.length === 0) {
                adminSelect.innerHTML = '<option value="">No admins found in this division</option>';
                adminSelect.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error fetching admins:', error);
            adminSelect.innerHTML = '<option value="">Error loading admins</option>';
            adminSelect.disabled = true;
            
            // Show user-friendly error message
            if (window.showMessage) {
                showMessage('Error loading admins for selected division', 'error');
            }
        });
    }

    // Event listener for division change
    divisionSelect.addEventListener('change', updateAdminOptions);

    // Initial load - if division is pre-selected (e.g., during edit)
    if (divisionSelect.value) {
        updateAdminOptions();
    }

    // Form validation enhancement
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const divisionValue = divisionSelect.value;
            const adminValue = adminSelect.value;

            if (!divisionValue) {
                e.preventDefault();
                alert('Please select a division first.');
                divisionSelect.focus();
                return;
            }

            if (!adminValue) {
                e.preventDefault();
                alert('Please select an admin for the project.');
                adminSelect.focus();
                return;
            }
        });
    }
});

// Utility function for showing messages (if you have a global message system)
function showMessage(message, type = 'info') {
    // You can customize this based on your existing message system
    // For example, if you're using Bootstrap toasts or alerts
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Example implementation with Bootstrap alerts
    const alertContainer = document.getElementById('alert-container');
    if (alertContainer) {
        const alertClass = type === 'error' ? 'alert-danger' : 'alert-info';
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        alertContainer.innerHTML = alertHtml;
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = alertContainer.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }
}