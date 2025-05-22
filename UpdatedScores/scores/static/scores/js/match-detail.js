/**
 * match-detail.js - Optimized JavaScript for match detail page
 * Handles timeline visualization, player ratings display and dynamic content loading
 */

// Cache DOM elements for better performance
const domCache = {};

// Initialize the match detail page functionality
function initMatchDetail() {
    // Cache commonly accessed DOM elements
    cacheElements();
    
    // Initialize timeline if present
    if (domCache.timeline) {
        initTimeline();
    }
    
    // Initialize tabbed content with lazy loading
    initTabbedContent();
    
    // Initialize tooltips
    initTooltips();
    
    // Add live polling for live matches
    if (isLiveMatch()) {
        initLivePolling();
    }
}

// Cache DOM elements for better performance
function cacheElements() {
    domCache.timeline = document.querySelector('.timeline');
    domCache.tabNavLinks = document.querySelectorAll('.nav-link');
    domCache.tabContents = document.querySelectorAll('.tab-pane');
    domCache.liveIndicator = document.querySelector('.live-indicator');
    domCache.countdownTimer = document.querySelector('.countdown-timer');
    domCache.playerRatings = document.querySelectorAll('.rating-circle');
    domCache.matchHeader = document.querySelector('.match-header');
}

// Initialize the match timeline visualization
function initTimeline() {
    // The timeline events are already added via the server-side rendering
    // Add event listeners for interactive features
    const timelineEvents = document.querySelectorAll('.timeline-event');
    
    timelineEvents.forEach(event => {
        event.addEventListener('mouseenter', showEventTooltip);
        event.addEventListener('mouseleave', hideEventTooltip);
        event.addEventListener('click', highlightEvent);
    });
}

// Show tooltip for timeline event
function showEventTooltip(e) {
    const event = e.currentTarget;
    const minute = event.getAttribute('data-minute');
    const player = event.getAttribute('data-player');
    const description = event.getAttribute('data-description');
    
    const tooltip = document.createElement('div');
    tooltip.className = 'timeline-tooltip';
    tooltip.innerHTML = `<strong>${minute}'</strong> - ${player}: ${description}`;
    
    tooltip.style.position = 'absolute';
    tooltip.style.left = `${event.offsetLeft}px`;
    tooltip.style.top = `${event.offsetTop - 40}px`;
    
    document.querySelector('.timeline-container').appendChild(tooltip);
}

// Hide tooltip for timeline event
function hideEventTooltip() {
    const tooltip = document.querySelector('.timeline-tooltip');
    if (tooltip) {
        tooltip.parentNode.removeChild(tooltip);
    }
}

// Highlight selected event
function highlightEvent(e) {
    // Remove highlight from other events
    document.querySelectorAll('.timeline-event.highlight').forEach(el => {
        el.classList.remove('highlight');
    });
    
    // Add highlight to current event
    e.currentTarget.classList.add('highlight');
    
    // Scroll to corresponding event in event list if available
    const minute = e.currentTarget.getAttribute('data-minute');
    const eventItem = document.querySelector(`.event-list-item[data-minute="${minute}"]`);
    if (eventItem) {
        eventItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        eventItem.classList.add('highlight');
        
        // Remove highlight after a delay
        setTimeout(() => {
            eventItem.classList.remove('highlight');
        }, 3000);
    }
}

// Initialize tabbed content with lazy loading
function initTabbedContent() {
    // Add click event handlers to tabs
    domCache.tabNavLinks.forEach(tabLink => {
        tabLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the target tab
            const targetId = this.getAttribute('href');
            const targetTab = document.querySelector(targetId);
            
            // Hide all tabs and show the target tab
            domCache.tabContents.forEach(tab => {
                tab.classList.remove('show', 'active');
            });
            targetTab.classList.add('show', 'active');
            
            // Update active state on nav links
            domCache.tabNavLinks.forEach(link => {
                link.classList.remove('active');
            });
            this.classList.add('active');
            
            // If this is the statistics tab and it has a lazy-load attribute, load the content
            if (targetId === '#statistics' && targetTab.getAttribute('data-lazy-load')) {
                loadStatistics(targetTab);
                targetTab.removeAttribute('data-lazy-load');
            }
        });
    });
}

// Initialize tooltips
function initTooltips() {
    // Find elements with tooltip attribute and initialize them
    const tooltipElements = document.querySelectorAll('[data-toggle="tooltip"]');
    tooltipElements.forEach(el => {
        el.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'custom-tooltip';
            tooltip.textContent = this.getAttribute('title');
            
            document.body.appendChild(tooltip);
            positionTooltip(tooltip, this);
            
            this.addEventListener('mouseleave', function() {
                document.body.removeChild(tooltip);
            }, { once: true });
        });
    });
}

// Position a tooltip relative to its trigger element
function positionTooltip(tooltip, element) {
    const rect = element.getBoundingClientRect();
    tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
    tooltip.style.left = `${rect.left + (rect.width/2) - (tooltip.offsetWidth/2)}px`;
}

// Check if current match is live
function isLiveMatch() {
    return domCache.liveIndicator !== null;
}

// Initialize polling for live match updates
function initLivePolling() {
    // Poll for updates every 60 seconds
    const matchId = domCache.matchHeader.getAttribute('data-match-id');
    setInterval(() => {
        fetchLiveMatchUpdates(matchId);
    }, 60000);
}

// Fetch live updates for the match
function fetchLiveMatchUpdates(matchId) {
    fetch(`/api/matches/${matchId}/live-updates/`)
        .then(response => response.json())
        .then(data => {
            updateMatchData(data);
        })
        .catch(error => {
            console.error('Error fetching live updates:', error);
        });
}

// Update match data with live information
function updateMatchData(data) {
    // Update score if changed
    if (data.score) {
        document.querySelector('.score-display').textContent = data.score;
    }
    
    // Update timeline with new events
    if (data.newEvents && data.newEvents.length > 0) {
        updateTimeline(data.newEvents);
    }
    
    // Update match statistics if changed
    if (data.statistics) {
        updateStatistics(data.statistics);
    }
}

// Update timeline with new events
function updateTimeline(newEvents) {
    // Implementation depends on the structure of timeline in HTML
    newEvents.forEach(event => {
        // Add new event to timeline
        addEventToTimeline(event);
        
        // Add event to event list
        addEventToEventList(event);
    });
}

// Add an event to the timeline
function addEventToTimeline(event) {
    const timeline = domCache.timeline;
    
    if (!timeline) return;
    
    const eventEl = document.createElement('div');
    eventEl.className = `timeline-event ${event.type} ${event.team}`;
    eventEl.style.left = `${(event.minute / 90) * 100}%`;
    eventEl.setAttribute('data-minute', event.minute);
    eventEl.setAttribute('data-player', event.player);
    eventEl.setAttribute('data-description', event.description);
    
    // Create minute indicator
    const minuteEl = document.createElement('div');
    minuteEl.className = 'minute';
    minuteEl.textContent = event.minute + "'";
    eventEl.appendChild(minuteEl);
    
    // Add to timeline
    timeline.appendChild(eventEl);
    
    // Add event listeners
    eventEl.addEventListener('mouseenter', showEventTooltip);
    eventEl.addEventListener('mouseleave', hideEventTooltip);
    eventEl.addEventListener('click', highlightEvent);
}

// Add an event to the event list
function addEventToEventList(event) {
    const eventsList = document.querySelector('.match-events-list');
    
    if (!eventsList) return;
    
    const eventEl = document.createElement('li');
    eventEl.className = `list-group-item event-list-item ${event.type}`;
    eventEl.setAttribute('data-minute', event.minute);
    
    eventEl.innerHTML = `
        <span class="event-time">${event.minute}'</span>
        <span class="event-icon"></span>
        <span class="event-player">${event.player}</span>
        <span class="event-description">${event.description}</span>
    `;
    
    eventsList.appendChild(eventEl);
}

// Update statistics with new data
function updateStatistics(statistics) {
    // Update possession
    if (statistics.possession) {
        document.querySelector('.home-possession').textContent = statistics.possession.home + '%';
        document.querySelector('.away-possession').textContent = statistics.possession.away + '%';
        document.querySelector('.possession-bar .home-bar').style.width = statistics.possession.home + '%';
        document.querySelector('.possession-bar .away-bar').style.width = statistics.possession.away + '%';
    }
    
    // Update other stats as needed
}

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', initMatchDetail);
