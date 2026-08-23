// gallery.js file

const galleryContainer = document.querySelector('.gallery-container');

// Function to fetch images from the server
async function fetchImages() {
    try {
        const response = await fetch('/api/images');
        const images = await response.json();
        displayImages(images);
    } catch (error) {
        console.error('Error fetching images:', error);
    }
}

const placeholderSrc = 'data:image/png;base64,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';

const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (!entry.isIntersecting) {
            return;
        }

        const img = entry.target;
        const src = img.dataset.src;
        if (src) {
            img.src = src;
            img.removeAttribute('data-src');
        }

        observer.unobserve(img);
    });
}, {
    rootMargin: '200px 0px',
    threshold: 0.1,
});

// Function to display images in the gallery
function displayImages(images) {
    const imageGrid = document.querySelector('#imageGrid');
    images.images.forEach(image => {
        const imgDiv = document.createElement('div');
        imgDiv.classList.add('item');

        const imgElement = document.createElement('img');
        imgElement.src = placeholderSrc;
        imgElement.dataset.src = `http://192.168.100.2:8000/${image.filename}`;
        imgElement.alt = image.description || 'Image';
        imgElement.loading = 'lazy';
        imgElement.classList.add('gallery-image');
        imgElement.addEventListener('error', () => {
            imgElement.classList.add('broken-image');
        });

        imgDiv.appendChild(imgElement);
        imageGrid.appendChild(imgDiv);

        if ('IntersectionObserver' in window) {
            imageObserver.observe(imgElement);
        } else {
            imgElement.src = imgElement.dataset.src;
            imgElement.removeAttribute('data-src');
        }
        imgElement.addEventListener('click', () => {
            const overlay = document.querySelector('.image-expanded');
            const image = overlay.querySelector('#expanded-image');
            const description = overlay.querySelector('#image-description');
            description.textContent = imgElement.alt || 'No description available';
            image.src = imgElement.src;
            overlay.style.display = 'flex';
        });
    });
}

// Fetch and display images when the page loads
window.addEventListener('DOMContentLoaded', fetchImages);

function performSearch(query) {
    const searchOverlay = document.querySelector('.search-overlay');
    const imageGrid = document.querySelector('#imageGrid');

    // Clear previous search results
    imageGrid.innerHTML = '';
    
    // Fetch search results from the server
    fetch(`/api/search?query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            // Display search results
            displayImages(data);
        })
        .catch(error => {
            console.error('Error performing search:', error);
        });
}

// Event listener for the search button
const searchBtn = document.querySelector('#searchBtn');
searchBtn.addEventListener('click', () => {
    const query = document.querySelector('#mainSearch').value;
    document.querySelector('.image-grid').innerHTML = '';
    const loading = document.createElement('img');
    loading.src = 'https://via.placeholder.com/300x300?text=Loading...';
    loading.classList.add('loading-image');
    document.querySelector('.image-grid').appendChild(loading);

    performSearch(query);
}); 


const closeBtn = document.querySelector('#close-btn');
closeBtn.addEventListener('click', () => {
    const overlay = document.querySelector('.image-expanded');
    overlay.style.display = 'none';
});
