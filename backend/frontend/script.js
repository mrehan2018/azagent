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