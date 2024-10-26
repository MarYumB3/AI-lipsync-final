document.getElementById('lip-sync-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const formData = new FormData(this);
    const progressPopup = document.getElementById('progress-popup');
    const progressPercentage = document.getElementById('progress-percentage');

    // Show the progress popup
    progressPopup.classList.remove('hidden');

    // Send the form data to the Flask backend
    fetch('/lip-sync', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        
        // Start listening for progress updates
        const eventSource = new EventSource('/lip-sync/process-status');

        eventSource.onmessage = function(event) {
            const progress = event.data;
            progressPercentage.textContent = `${progress}%`;

            // Redirect to preview page when done
            if (progress === '100') {
                eventSource.close();
                window.location.href = '/preview';
            }
        };

        eventSource.onerror = function() {
            eventSource.close();
            alert('Error during processing.');
        };
    })
    .catch(error => {
        console.error('Error during submission:', error);
        alert('An error occurred during submission.');
    });
});

function checkStatus() {
    fetch('/check-status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'complete') {
                window.location.href = '/preview';
            } else if (data.status === 'not_logged_in') {
                window.location.href = '/login';
            } else {
                setTimeout(checkStatus, 2000);  // Check again in 2 seconds
            }
        })
        .catch(error => console.error('Error checking status:', error));
}

// Only start checking status after form submission
// window.onload = checkStatus; // Commented to avoid polling before submission
