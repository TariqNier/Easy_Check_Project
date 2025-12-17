const registerUser = async (phone, password) => {
  try {
    const response = await fetch('http://localhost:8000/api/auth/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        phone_number: phone,
        password: password
      })
    });

    const data = await response.json();
    
    if (response.ok) {
      console.log("Success! Username is:", data.username);
    } else {
      console.error("Error:", data);
    }
  } catch (error) {
    console.error("Network Error:", error);
  }
};