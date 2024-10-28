document.addEventListener('DOMContentLoaded', function() {
    const lipSyncForm = document.getElementById('lip-sync-form');
    const downloadLink = document.getElementById('downloadLink');
    const feedbackForm = document.getElementById('feedback-form');

    if (lipSyncForm) {
        lipSyncForm.addEventListener('submit', function(event) {
            // Prevent default form submission for fetch handling
            event.preventDefault();

            const formData = new FormData(this);
            console.log('Form submitted, starting process...');

            // Send the form data to the Flask backend
            fetch('/lip-sync', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                console.log('Form submitted successfully, checking for response...');
                return response.json(); // Assuming the backend responds with JSON
            })
            .then(data => {
                // Here you would handle the response from the server
                console.log('Server response:', data);

                // Assuming a success response contains a link to the video preview
                if (data.redirect_url) {
                    // Redirect to the preview page
                    window.location.href = data.redirect_url;
                } else {
                    alert('No download link available.');
                }
            })
            .catch(error => {
                console.error('Error during submission:', error);
                alert('An error occurred during submission.');
            });
        });
    }

    // Logic for downloading the processed video
    if (downloadLink) {
        downloadLink.addEventListener('click', function () {
            setTimeout(function() {
                window.location.href = "{{ url_for('feedback') }}";
            }, 1000); // Delay to allow download to initiate
        });
    }

    // Feedback form handling
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent default form submission

            const feedbackData = new FormData(this);
            console.log('Submitting feedback...');

            fetch('/submit_feedback', {
                method: 'POST',
                body: feedbackData
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                console.log('Feedback submission response:', data);
                alert('Feedback submitted successfully!');
                // Optionally, redirect to a different page or reset the form
                feedbackForm.reset();
            })
            .catch(error => {
                console.error('Error during feedback submission:', error);
                alert('An error occurred during feedback submission.');
            });
        });
    }
});
