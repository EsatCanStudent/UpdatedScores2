/**
 * Live match functionality
 * This file contains code for live match updates and interactive features
 */

// Keep track of match elements on the page
const liveMatchElements = {};

// Function to initialize live match tracking
function initializeLiveMatches() {
    // Find all live match containers
    const liveMatches = document.querySelectorAll('.match-card[data-status="live"]');
    
    liveMatches.forEach(match => {
        const matchId = match.dataset.matchId;
        const minuteElement = match.querySelector('.match-minute');
        const scoreElement = match.querySelector('.score-display');
        const statusElement = match.querySelector('.match-status');
        
        // Store references to elements for this match
        liveMatchElements[matchId] = {
            container: match,
            minute: minuteElement,
            score: scoreElement,
            status: statusElement,
            lastUpdated: new Date(),
            events: []
        };
    });
    
    // If we have live matches, start the update cycle
    if (liveMatches.length > 0) {
        startLiveUpdates();
    }
}

// Function to start live updates
function startLiveUpdates() {
    // Update match times every second
    setInterval(updateMatchTimes, 1000);
    
    // Update match data (scores, events) from server every 30 seconds
    setInterval(refreshMatchData, 30000);
}

// Update displayed match times
function updateMatchTimes() {
    for (const matchId in liveMatchElements) {
        const match = liveMatchElements[matchId];
        const minuteElement = match.minute;
        
        if (!minuteElement) continue;
        
        // Parse current minute from element
        let currentMinute = parseInt(minuteElement.dataset.minute || 0);
        let period = minuteElement.dataset.period || 'first';
        
        // Only update if match is actually live (not halftime or finished)
        if (match.status.textContent.toLowerCase() === 'live') {
            // Update based on period
            if (period === 'first') {
                if (currentMinute < 45) {
                    currentMinute++;
                    minuteElement.textContent = `${currentMinute}'`;
                    minuteElement.dataset.minute = currentMinute;
                }
            } else if (period === 'second') {
                if (currentMinute < 90) {
                    currentMinute++;
                    minuteElement.textContent = `${currentMinute}'`;
                    minuteElement.dataset.minute = currentMinute;
                }
            } else if (period === 'extraFirst') {
                if (currentMinute < 105) {
                    currentMinute++;
                    minuteElement.textContent = `${currentMinute}'`;
                    minuteElement.dataset.minute = currentMinute;
                }
            } else if (period === 'extraSecond') {
                if (currentMinute < 120) {
                    currentMinute++;
                    minuteElement.textContent = `${currentMinute}'`;
                    minuteElement.dataset.minute = currentMinute;
                }
            }
            
            // Add pulse effect class to indicate live status
            match.container.classList.add('pulse-live');
        }
    }
}

// Refresh match data from server
function refreshMatchData() {
    // Collect IDs of live matches
    const matchIds = Object.keys(liveMatchElements);
    
    if (matchIds.length === 0) return;
    
    // Make AJAX request to get updated match data
    fetch(`/api/live-matches/?ids=${matchIds.join(',')}`)
        .then(response => response.json())
        .then(data => {
            // Process each match update
            data.matches.forEach(matchData => {
                updateMatchDisplay(matchData);
            });
        })
        .catch(error => {
            console.error('Error fetching live match updates:', error);
        });
}

// Update match display with fresh data
function updateMatchDisplay(matchData) {
    const matchId = matchData.id;
    const match = liveMatchElements[matchId];
    
    if (!match) return;
    
    // Update score if changed
    if (matchData.score && match.score.textContent !== matchData.score) {
        // Flash animation for score change
        match.score.classList.add('score-changed');
        match.score.textContent = matchData.score;
        
        // Remove animation class after animation completes
        setTimeout(() => {
            match.score.classList.remove('score-changed');
        }, 2000);
    }
    
    // Update match status if changed
    if (matchData.status && match.status.textContent !== matchData.status) {
        match.status.textContent = matchData.status;
        
        // Update period if needed
        if (matchData.period) {
            match.minute.dataset.period = matchData.period;
        }
    }
    
    // Update match minute if provided and different
    if (matchData.minute) {
        match.minute.dataset.minute = matchData.minute;
        match.minute.textContent = `${matchData.minute}'`;
    }
    
    // Process any new events
    if (matchData.events && matchData.events.length > 0) {
        // Get new events (events not already in our list)
        const existingEventIds = new Set(match.events.map(e => e.id));
        const newEvents = matchData.events.filter(e => !existingEventIds.has(e.id));
        
        if (newEvents.length > 0) {
            // Add new events to our tracking
            match.events = [...match.events, ...newEvents];
            
            // Display notification for new events
            newEvents.forEach(event => {
                showEventNotification(matchId, event);
            });
            
            // Update events display if we're on a match detail page
            const eventsContainer = document.querySelector(`.match-events-container[data-match-id="${matchId}"]`);
            if (eventsContainer) {
                // Render new events
                newEvents.forEach(event => {
                    renderEventCard(eventsContainer, event);
                });
            }
        }
    }
    
    // Update last updated timestamp
    match.lastUpdated = new Date();
}

// Show notification for new match event
function showEventNotification(matchId, event) {
    const match = liveMatchElements[matchId];
    const notificationContainer = document.getElementById('event-notifications');
    
    if (!notificationContainer) return;
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${getEventColorClass(event.type)} alert-dismissible fade show`;
    notification.role = 'alert';
    
    // Format event message
    let message = '';
    if (event.type === 'GOAL') {
        message = `⚽ GOAL! ${event.playerName} scores for ${event.teamName} (${event.minute}')`;
    } else if (event.type === 'YELLOW') {
        message = `🟨 Yellow card: ${event.playerName} (${event.teamName}) at ${event.minute}'`;
    } else if (event.type === 'RED') {
        message = `🟥 Red card: ${event.playerName} (${event.teamName}) at ${event.minute}'`;
    } else if (event.type === 'SUB') {
        message = `🔄 Substitution for ${event.teamName}: ${event.playerName} at ${event.minute}'`;
    }
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container and set timeout to remove
    notificationContainer.appendChild(notification);
    
    // Remove after 10 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 500);
    }, 10000);
}

// Get Bootstrap color class for event type
function getEventColorClass(eventType) {
    switch (eventType) {
        case 'GOAL': return 'success';
        case 'YELLOW': return 'warning';
        case 'RED': return 'danger';
        case 'SUB': return 'info';
        default: return 'primary';
    }
}

// Render an event card in the events container
function renderEventCard(container, event) {
    const eventCard = document.createElement('div');
    eventCard.className = `card event-card ${event.type.toLowerCase()} mb-2`;
    eventCard.dataset.eventId = event.id;
    
    eventCard.innerHTML = `
        <div class="card-body py-2">
            <div class="d-flex align-items-center">
                <div class="event-minute badge bg-secondary me-2">${event.minute}'</div>
                <div class="event-icon me-2">
                    ${getEventIcon(event.type)}
                </div>
                <div class="event-details flex-grow-1">
                    <strong>${event.playerName}</strong>
                    <div class="small text-muted">${event.teamName}</div>
                </div>
            </div>
        </div>
    `;
    
    // Add to beginning if it's a new event (most recent)
    container.prepend(eventCard);
}

// Get icon for event type
function getEventIcon(eventType) {
    switch (eventType) {
        case 'GOAL': return '<i class="bi bi-bullseye text-success"></i>';
        case 'YELLOW': return '<i class="bi bi-card-fill text-warning"></i>';
        case 'RED': return '<i class="bi bi-card-fill text-danger"></i>';
        case 'SUB': return '<i class="bi bi-arrow-left-right text-info"></i>';
        default: return '<i class="bi bi-clock"></i>';
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeLiveMatches();
    
    // Set up event notification area if not exists
    if (!document.getElementById('event-notifications')) {
        const notifications = document.createElement('div');
        notifications.id = 'event-notifications';
        notifications.className = 'position-fixed bottom-0 end-0 p-3';
        notifications.style.zIndex = "1050";
        document.body.appendChild(notifications);
    }
});
