/**
 * Match statistics chart rendering functions
 * This file contains all the chart-related code for the football scores application
 */

// Function to create radar chart for team comparison
function createTeamComparisonChart(elementId, homeTeam, awayTeam, homeStats, awayStats) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Get statistics to display
    const labels = [
        'Possession', 'Shots', 'Shots On Target', 
        'Corners', 'Fouls', 'Passes', 'Pass Accuracy'
    ];
    
    // Set color schemes for teams
    const homeColor = '#0d6efd';
    const awayColor = '#dc3545';
    
    const chart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: homeTeam,
                    data: homeStats,
                    backgroundColor: `${homeColor}33`,
                    borderColor: homeColor,
                    pointBackgroundColor: homeColor,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: homeColor
                },
                {
                    label: awayTeam,
                    data: awayStats,
                    backgroundColor: `${awayColor}33`,
                    borderColor: awayColor,
                    pointBackgroundColor: awayColor,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: awayColor
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: {
                        display: true
                    },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
    
    return chart;
}

// Function to create player ratings chart
function createPlayerRatingsChart(elementId, players, ratings) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: players,
            datasets: [{
                label: 'Player Ratings',
                data: ratings,
                backgroundColor: ratings.map(rating => {
                    if (rating >= 8) return '#198754';  // Great performance
                    if (rating >= 7) return '#0dcaf0';  // Good performance
                    if (rating >= 6) return '#ffc107';  // Average performance
                    return '#dc3545';                   // Poor performance
                }),
                borderColor: 'rgba(0, 0, 0, 0.1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10,
                    title: {
                        display: true,
                        text: 'Rating (out of 10)'
                    }
                }
            }
        }
    });
    
    return chart;
}

// Function to create head-to-head comparison chart
function createHeadToHeadChart(elementId, homeTeam, awayTeam, homeWins, awayWins, draws) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: [`${homeTeam} Wins`, `${awayTeam} Wins`, 'Draws'],
            datasets: [{
                data: [homeWins, awayWins, draws],
                backgroundColor: ['#0d6efd', '#dc3545', '#6c757d'],
                borderColor: ['#fff', '#fff', '#fff'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = homeWins + awayWins + draws;
                            const percentage = Math.round((context.raw / total) * 100);
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    return chart;
}

// Function for creating match timeline visualization
function createMatchTimeline(elementId, events) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Process events into datasets
    const homeGoals = [];
    const awayGoals = [];
    const homeCards = [];
    const awayCards = [];
    
    events.forEach(event => {
        if (event.type === 'GOAL') {
            if (event.team === 'home') {
                homeGoals.push({x: event.minute, y: 1});
            } else {
                awayGoals.push({x: event.minute, y: 0});
            }
        } else if (event.type === 'YELLOW' || event.type === 'RED') {
            if (event.team === 'home') {
                homeCards.push({x: event.minute, y: 1, type: event.type});
            } else {
                awayCards.push({x: event.minute, y: 0, type: event.type});
            }
        }
    });
    
    const chart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Home Goals',
                    data: homeGoals,
                    backgroundColor: '#198754',
                    pointRadius: 6,
                    pointStyle: 'triangle'
                },
                {
                    label: 'Away Goals',
                    data: awayGoals,
                    backgroundColor: '#198754',
                    pointRadius: 6,
                    pointStyle: 'triangle'
                },
                {
                    label: 'Home Cards',
                    data: homeCards,
                    backgroundColor: (context) => {
                        const index = context.dataIndex;
                        const type = homeCards[index]?.type;
                        return type === 'RED' ? '#dc3545' : '#ffc107';
                    },
                    pointRadius: 4,
                    pointStyle: 'rect'
                },
                {
                    label: 'Away Cards',
                    data: awayCards,
                    backgroundColor: (context) => {
                        const index = context.dataIndex;
                        const type = awayCards[index]?.type;
                        return type === 'RED' ? '#dc3545' : '#ffc107';
                    },
                    pointRadius: 4,
                    pointStyle: 'rect'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    min: 0,
                    max: 90,
                    title: {
                        display: true,
                        text: 'Match Minute'
                    }
                },
                y: {
                    display: false,
                    min: -0.5,
                    max: 1.5
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.dataset.data[context.dataIndex];
                            let label = context.dataset.label || '';
                            
                            if (label) {
                                label += ': ';
                            }
                            
                            if (point && 'type' in point) {
                                return label + `${point.type} Card at ${point.x}'`;
                            }
                            
                            return label + `Goal at ${point.x}'`;
                        }
                    }
                }
            }
        }
    });
    
    return chart;
}
