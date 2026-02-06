
document.addEventListener('DOMContentLoaded', function() {
    // File name updating
    function updateFileName(value) {
        document.getElementById('export-filename').value = value;
        document.getElementById('download-filename').value = value;
    }
    
    // Make updateFileName available globally
    window.updateFileName = updateFileName;

    // Modal functionality
    const modal = document.getElementById('addVariableModal');
    const modalTitle = document.querySelector('.modal-title');
    const form = modal.querySelector('form');
    const closeBtn = document.querySelector('.close');
    const submitBtn = form.querySelector('button[name="add_variable"]');
    let isEditing = false;
    let editingName = '';
    
    window.openModal = function() {
        if (modal) {
            isEditing = false;
            modalTitle.textContent = 'Add Item';
            submitBtn.textContent = 'Add Item';
            form.reset();
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }
    
    window.editVariable = function(variable) {
        if (modal) {
            isEditing = true;
            editingName = variable.name;
            modalTitle.textContent = 'Edit Variable';
            submitBtn.textContent = 'Update Variable';
            
            // Fill form with variable data
            form.name.value = variable.name;
            form.lowerBound.value = variable.lowerBound;
            form.upperBound.value = variable.upperBound;
            form.cost.value = variable.cost;
            form.profit.value = variable.profit;
            form.multiplier.value = variable.multiplier;
            
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }
    
    window.closeModal = function() {
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
            isEditing = false;
            form.reset();
        }
    }
    
    // Handle form submission
    form.addEventListener('submit', function(e) {
        if (isEditing) {
            e.preventDefault();
            const formData = new FormData(form);
            formData.append('old_name', editingName);
            
            fetch('/update_variable', {
                method: 'POST',
                body: formData
            }).then(async response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    const data = await response.json();
                    throw new Error(data.message || 'Failed to update variable');
                }
            }).catch(error => {
                showError('Error updating variable: ' + error.message);
            });
        }
    });
    
    // Function to display error messages
    function showError(message) {
        alert(message);
    }
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target === modal) {
            closeModal();
        }
    }
    
    // Close modal when clicking the X
    if (closeBtn) {
        closeBtn.onclick = closeModal;
    }
    
    // Close modal when pressing Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
});
