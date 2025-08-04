async function lookupUser() {
  const role = document.getElementById('role').value;
  const userId = document.getElementById('userId').value;
  const resultBox = document.getElementById('result');

  if (!userId) {
    resultBox.textContent = 'Please enter a user ID.';
    resultBox.className = 'error';
    return;
  }

  const url = `/api/v1/${role}s/${userId}`;

  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Status ${response.status}`);
    const data = await response.json();
    resultBox.textContent = JSON.stringify(data, null, 2);
    resultBox.className = 'success';
  } catch (error) {
    resultBox.textContent = `Error: ${error.message}`;
    resultBox.className = 'error';
  }
}

// Additional utility functions for your existing HTML
async function fetchUser(userType) {
  const idField = document.getElementById(`${userType}Id`);
  const id = idField.value.trim();
  
  if (!id) {
    displayResult({ error: `Please enter a ${userType} ID` }, true);
    return;
  }

  try {
    const response = await fetch(`/api/v1/${userType}s/${id}`);
    const data = await response.json();
    
    if (response.ok) {
      displayResult(data, false);
    } else {
      displayResult(data, true);
    }
  } catch (error) {
    displayResult({ error: `Network error: ${error.message}` }, true);
  }
}

async function sendChat() {
  const role = document.getElementById('userRole').value;
  const topic = document.getElementById('topic').value.trim();
  const context = document.getElementById('context').value.trim();

  if (!topic || !context) {
    displayResult({ error: 'Please fill in both topic and context' }, true);
    return;
  }

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_role: role,
        topic: topic,
        context: context
      })
    });

    const data = await response.json();
    displayResult(data, !response.ok);
  } catch (error) {
    displayResult({ error: `Network error: ${error.message}` }, true);
  }
}

async function checkHealth() {
  try {
    const response = await fetch('/health');
    const data = await response.json();
    displayResult(data, false);
  } catch (error) {
    displayResult({ error: `Network error: ${error.message}` }, true);
  }
}

function displayResult(data, isError) {
  const resultElement = document.getElementById('result');
  resultElement.textContent = JSON.stringify(data, null, 2);
  resultElement.className = isError ? 'error' : 'success';
}

async function sendMessage() {
  const role = document.getElementById("role").value;
  const userId = document.getElementById("userId").value;
  const userInput = document.getElementById("userInput").value;

  if (!userId || !userInput) {
    showError("Please enter both User ID and your question");
    return;
  }

  showLoading();

  try {
      // First get the full user data
      const userUrl = `/api/v1/${role}/${userId}`;
      const userResponse = await fetch(userUrl);
      const userData = await userResponse.json();

      // Send chat with full user context
      const body = {
          user_role: role.slice(0, -1), // "students" => "student"
          topic: userInput,
          context: JSON.stringify(userData) // ✅ Send full user data as JSON string
      };

      const chatResponse = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
      });

      const chatData = await chatResponse.json();
      showChatResponse(userData.name || userId, userInput, chatData.reply);
      
  } catch (error) {
      showError(`Chat Error: ${error.message}`);
  }
}

async function uploadFile() {
  const fileInput = document.getElementById('fileInput');
  
  if (!fileInput.files[0]) {
    document.getElementById('responseArea').innerHTML = `
      <p><strong>Error:</strong> Please select a file to upload</p>
    `;
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    // Fixed the URL (was missing colon after https)
    const response = await fetch("https://gaief-function-app-hbape9dmfph0bkge.canadacentral-01.azurewebsites.net/api/uploadOCRSummary", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    document.getElementById('responseArea').innerHTML = `
      <p><strong>File:</strong> ${fileInput.files[0].name}</p>
      <p><strong>File Summary:</strong> ${JSON.stringify(data, null, 2)}</p>
    `;
  } catch (error) {
    document.getElementById('responseArea').innerHTML = `
      <p><strong>Upload Error:</strong> ${error.message}</p>
    `;
  }
}

// Additional utility functions for better UX
function clearResponse() {
  document.getElementById('responseArea').innerHTML = '';
}

function showLoading() {
  document.getElementById('responseArea').innerHTML = '<p>Loading...</p>';
}

// Enhanced sendMessage with loading state
async function sendMessageEnhanced() {
  const role = document.getElementById('role').value;
  const userId = document.getElementById('userId').value;
  const userInput = document.getElementById('userInput').value;

  if (!userId || !userInput) {
    document.getElementById('responseArea').innerHTML = `
      <p><strong>Error:</strong> Please enter both User ID and your question</p>
    `;
    return;
  }

  showLoading();

  try {
    // First get user data
    const userUrl = `https://gaief-demo-app-eyd2anfafbaxgghn.centralus-01.azurewebsites.net/api/v1/${role}/${userId}`;
    const userResponse = await fetch(userUrl);
    const userData = await userResponse.json();

    // Then send chat request
    const chatUrl = `https://gaief-demo-app-eyd2anfafbaxgghn.centralus-01.azurewebsites.net/chat`;
    const chatResponse = await fetch(chatUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_role: role.slice(0, -1), // Remove 's' from end (students -> student)
        topic: userInput,
        context: JSON.stringify(userData)
      })
    });

    const chatData = await chatResponse.json();

    document.getElementById('responseArea').innerHTML = `
      <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px;">
        <p><strong>User (${userData.name || userId}):</strong> ${userInput}</p>
      </div>
      <div style="background: #e8f4fd; padding: 10px; margin: 10px 0; border-radius: 5px;">
        <p><strong>AI Assistant:</strong> ${chatData.response || JSON.stringify(chatData, null, 2)}</p>
      </div>
    `;
  } catch (error) {
    document.getElementById('responseArea').innerHTML = `
      <p><strong>Error:</strong> ${error.message}</p>
    `;
  }
}

// Update the sendMessage function to use the enhanced version
async function sendMessage() {
  await sendMessageEnhanced();
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, initializing event listeners...");
    
    // Check if sendBtn exists and add event listener
    const sendBtn = document.getElementById("sendBtn");
    if (sendBtn) {
        sendBtn.addEventListener("click", handleSendBtn);
        console.log("sendBtn event listener added");
    } else {
        console.error("sendBtn not found!");
    }
});

// Handle Send Query button
async function handleSendBtn() {
    console.log("handleSendBtn called");
    
    const role = document.getElementById("role").value;
    const userId = document.getElementById("userId").value;
    const userQuery = document.getElementById("query").value;

    console.log("Values:", { role, userId, userQuery });

    if (!userId) {
        showError("Please enter a User ID");
        return;
    }

    // Show loading
    showLoading();

    const apiUrl = `/api/v1/${role}/${userId}`;
    console.log("API URL:", apiUrl);

    try {
        const response = await fetch(apiUrl);
        console.log("Response status:", response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log("Response data:", data);

        showSuccess(userQuery, data);
    } catch (error) {
        console.error("Fetch error:", error);
        showError(`Error: ${error.message}`);
    }
}

// AI Chat function
async function sendMessage() {
    console.log("sendMessage called");
    
    const role = document.getElementById("role").value;
    const userId = document.getElementById("userId").value;
    const userInput = document.getElementById("userInput").value;

    if (!userId || !userInput) {
        showError("Please enter both User ID and your question");
        return;
    }

    showLoading();

    try {
        // First get the full user data
        const userUrl = `/api/v1/${role}/${userId}`;
        const userResponse = await fetch(userUrl);
        const userData = await userResponse.json();

        // Send chat with full user context
        const body = {
            user_role: role.slice(0, -1), // "students" => "student"
            topic: userInput,
            context: JSON.stringify(userData) // ✅ Send full user data as JSON string
        };

        const chatResponse = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const chatData = await chatResponse.json();
        showChatResponse(userData.name || userId, userInput, chatData.reply);
        
    } catch (error) {
        showError(`Chat Error: ${error.message}`);
    }
}

// File Upload
async function uploadFile() {
    console.log("uploadFile called");
    
    const fileInput = document.getElementById("fileInput");
    
    if (!fileInput.files[0]) {
        showError("Please select a file to upload");
        return;
    }

    showLoading();

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const response = await fetch("https://gaief-function-app-hbape9dmfph0bkge.canadacentral-01.azurewebsites.net/api/uploadOCRSummary", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        showFileResponse(fileInput.files[0].name, data);
        
    } catch (error) {
        console.error("Upload error:", error);
        showError(`Upload Error: ${error.message}`);
    }
}

// Debug function
async function debugStudent() {
    console.log("debugStudent called");
    
    const userId = document.getElementById("userId").value;
    
    if (!userId) {
        showError("Please enter a user ID for debugging");
        return;
    }

    showLoading();

    try {
        const response = await fetch(`/debug/student/${userId}`);
        const data = await response.json();
        showDebugResponse(userId, data);
        
    } catch (error) {
        console.error("Debug error:", error);
        showError(`Debug Error: ${error.message}`);
    }
}

// UI Helper Functions
function showLoading() {
    document.getElementById('responseArea').innerHTML = `
        <div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
            <p>Loading...</p>
        </div>
    `;
}

function showError(message) {
    document.getElementById('responseArea').innerHTML = `
        <div style="background: #ffebee; padding: 10px; margin: 10px 0; border-radius: 5px; color: red; border: 1px solid #ff9999;">
            <p><strong>Error:</strong> ${message}</p>
        </div>
    `;
}

function showSuccess(title, message) {
    hideLoading();
    document.getElementById('responseArea').innerHTML = `
        <div class="bg-green-50 border border-green-200 rounded-xl p-6">
            <div class="flex items-center mb-3">
                <div class="text-green-500 text-2xl mr-3">✅</div>
                <h3 class="text-green-800 font-semibold text-lg">${title}</h3>
            </div>
            <p class="text-green-700">${message}</p>
        </div>
    `;
}

// Enhanced chat response display
function showChatResponse(userName, question, response) {
    hideLoading();
    document.getElementById('responseArea').innerHTML = `
        <div class="space-y-4">
            <div class="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <div class="flex items-start">
                    <div class="text-blue-500 text-xl mr-3">👤</div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-blue-800">${userName || 'User'}</h4>
                        <p class="text-blue-700">${question}</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-green-50 border border-green-200 rounded-xl p-4">
                <div class="flex items-start">
                    <div class="text-green-500 text-xl mr-3">🤖</div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-green-800">AI Assistant</h4>
                        <div class="text-green-700 whitespace-pre-wrap">${response}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Load user profile function
async function loadUserProfile() {
    const role = document.getElementById("role").value;
    const userId = document.getElementById("userId").value;
    
    if (!userId) {
        showError("Please enter a User ID");
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`/api/v1/${role}/${userId}`);
        const userData = await response.json();
        
        if (response.ok) {
            document.getElementById('responseArea').innerHTML = `
                <div class="bg-blue-50 border border-blue-200 rounded-xl p-6">
                    <div class="flex items-center mb-4">
                        <div class="text-blue-500 text-2xl mr-3">👤</div>
                        <h3 class="text-blue-800 font-semibold text-lg">Profile Loaded</h3>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-white p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-800 mb-2">Basic Info</h4>
                            <p><strong>Name:</strong> ${userData.name || 'N/A'}</p>
                            <p><strong>ID:</strong> ${userData.userId || userData.id}</p>
                            <p><strong>Role:</strong> ${role.slice(0, -1)}</p>
                        </div>
                        ${userData.grade ? `
                        <div class="bg-white p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-800 mb-2">Academic Info</h4>
                            <p><strong>Grade:</strong> ${userData.grade}</p>
                            <p><strong>Subjects:</strong> ${userData.subjects ? userData.subjects.join(', ') : 'N/A'}</p>
                        </div>
                        ` : ''}
                    </div>
                    ${userData.progress ? `
                    <div class="mt-4 bg-white p-4 rounded-lg">
                        <h4 class="font-semibold text-gray-800 mb-2">Progress</h4>
                        ${Object.entries(userData.progress).map(([subject, score]) => `
                            <div class="flex items-center justify-between mb-2">
                                <span class="font-medium">${subject}:</span>
                                <div class="flex items-center">
                                    <div class="w-32 bg-gray-200 rounded-full h-2 mr-2">
                                        <div class="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full" style="width: ${score}%;"></div>
                                    </div>
                                    <span class="text-sm font-semibold">${score}%</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    ` : ''}
                </div>
            `;
        } else {
            showError(userData.error || "User not found");
        }
    } catch (error) {
        showError(`Error loading profile: ${error.message}`);
    }
    
    hideLoading();
}

// Enhanced sendMessage function
async function sendMessage() {
    const role = document.getElementById("role").value;
    const userId = document.getElementById("userId").value;
    const message = document.getElementById("userInput").value;
    
    if (!userId || !message) {
        showError("Please enter both User ID and message");
        return;
    }
    
    showLoading();
    
    try {
        // Get user context first
        const userResponse = await fetch(`/api/v1/${role}/${userId}`);
        const userData = await userResponse.json();
        
        if (!userResponse.ok) {
            showError("User not found. Please check User ID.");
            return;
        }
        
        // Send chat request
        const chatResponse = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_role: role.slice(0, -1), // Remove 's' from role
                topic: message,
                context: JSON.stringify(userData)
            })
        });
        
        const chatData = await chatResponse.json();
        
        if (chatResponse.ok) {
            showChatResponse(userData.name, message, chatData.reply);
            // Clear input
            document.getElementById("userInput").value = '';
        } else {
            showError(chatData.error || "Chat failed");
        }
        
    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

// Enhanced show chat history function
async function showChatHistory() {
    const userId = document.getElementById("userId").value;
    const role = document.getElementById("role").value;
    
    if (!userId) {
        showError("Please enter a User ID to view chat history");
        return;
    }

    showLoading();

    try {
        const response = await fetch(`/debug/chat-history/${userId}?user_role=${role.slice(0, -1)}`);
        const data = await response.json();
        
        hideLoading();
        
        document.getElementById('responseArea').innerHTML = `
            <div class="bg-purple-50 border border-purple-200 rounded-xl p-6">
                <div class="flex items-center mb-4">
                    <div class="text-purple-500 text-2xl mr-3">📚</div>
                    <h3 class="text-purple-800 font-semibold text-lg">Chat History for ${userId}</h3>
                </div>
                <p class="text-purple-700 mb-4"><strong>Total Messages:</strong> ${data.chat_history_count || 0}</p>
                
                ${data.chat_history && data.chat_history.length > 0 ? `
                    <div class="space-y-3 max-h-96 overflow-y-auto">
                        ${data.chat_history.map(chat => `
                            <div class="bg-white border border-purple-100 rounded-lg p-4">
                                <div class="mb-2">
                                    <strong class="text-purple-800">Q:</strong> 
                                    <span class="text-gray-700">${chat.question}</span>
                                </div>
                                <div class="mb-2">
                                    <strong class="text-purple-800">A:</strong> 
                                    <span class="text-gray-700">${chat.answer}</span>
                                </div>
                                <div class="text-xs text-gray-500 text-right">
                                    ${chat.timestamp ? new Date(chat.timestamp).toLocaleString() : 'N/A'}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : '<p class="text-center text-purple-600">No chat history found</p>'}
            </div>
        `;
        
    } catch (error) {
        showError(`Error loading chat history: ${error.message}`);
    }
}

// File upload function
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const role = document.getElementById('role').value;
    
    if (!fileInput.files[0]) {
        showError('Please select a PDF file first');
        return;
    }
    
    showLoading();
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('role', role.slice(0, -1));
    formData.append('topic', 'Analyze this document');
    
    try {
        const response = await fetch('/upload-test', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('responseArea').innerHTML = `
                <div class="bg-purple-50 border border-purple-200 rounded-xl p-6">
                    <div class="flex items-center mb-4">
                        <div class="text-purple-500 text-2xl mr-3">📄</div>
                        <h3 class="text-purple-800 font-semibold text-lg">Document Analysis</h3>
                    </div>
                    <div class="bg-white p-4 rounded-lg mb-4">
                        <h4 class="font-semibold text-gray-800 mb-2">AI Response:</h4>
                        <p class="text-gray-700 whitespace-pre-wrap">${data.reply}</p>
                    </div>
                    <details class="bg-white p-4 rounded-lg">
                        <summary class="font-semibold text-gray-800 cursor-pointer">Extracted Text (Click to expand)</summary>
                        <pre class="text-sm text-gray-600 mt-2 whitespace-pre-wrap">${data.extracted_text}</pre>
                    </details>
                </div>
            `;
        } else {
            showError(data.error || 'Upload failed');
        }
    } catch (error) {
        showError(`Upload error: ${error.message}`);
    }
    
    hideLoading();
}

// Test chat endpoint function
async function testChatEndpoint() {
    showLoading();
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_role: "student",
                topic: "What is my math progress?",
                context: JSON.stringify({
                    "id": "stu_12345",
                    "userId": "stu_12345",
                    "name": "Aisha Khan",
                    "grade": "4",
                    "subjects": ["Math", "Science"],
                    "progress": {"Math": 88, "Science": 95}
                })
            })
        });

        const data = await response.json();
        
        hideLoading();
        
        document.getElementById('responseArea').innerHTML = `
            <div class="bg-blue-50 border border-blue-200 rounded-xl p-6">
                <div class="flex items-center mb-4">
                    <div class="text-blue-500 text-2xl mr-3">🧪</div>
                    <h3 class="text-blue-800 font-semibold text-lg">Chat Test Result</h3>
                </div>
                <pre class="bg-white p-4 rounded-lg text-sm overflow-x-auto">${JSON.stringify(data, null, 2)}</pre>
            </div>
        `;
        
    } catch (error) {
        showError(`Chat Test Error: ${error.message}`);
    }
}

// Parent portal functions (fetchStudentChat and fetchStudentProgress)
// Add your existing parent portal functions here...

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    console.log('GAIEF AI Assistant loaded with enhanced Tailwind UI');
});