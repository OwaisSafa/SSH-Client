# 🖥️ SSH Client

A modern, feature-rich SSH client with a graphical user interface built using CustomTkinter and Paramiko. This client provides a seamless and secure way to manage multiple SSH connections with an intuitive interface.

## ✨ Features

🔐 **Security**
- Secure password storage with encryption
- SSH key authentication support
- Auto-adding of host keys

🎨 **User Interface**
- Modern and intuitive graphical interface
- Dark and light theme support
- Customizable terminal font and size
- Multiple terminal tabs

🔄 **Session Management**
- Save and organize multiple SSH connections
- Import/Export session configurations
- Search functionality for saved sessions
- Command history navigation

⌨️ **Advanced Features**
- Keyboard shortcuts for quick navigation
- Real-time terminal output
- Session persistence
- Error handling and recovery

## 🛠️ Requirements

- Python 3.7+
- Dependencies (see `requirements.txt`):
  - paramiko (SSH protocol)
  - customtkinter (Modern UI)
  - cryptography (Encryption)
  - pytermgui (Terminal handling)

## 📦 Installation

1. Clone this repository:
```bash
git clone https://github.com/OwaisSafa/SSH-Client.git
cd SSH-Client
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Starting the Application
```bash
python main.py
```

### 🔑 Creating a New Session

1. Click on "File" → "New Session" or use `Ctrl+N`
2. Enter the session details:
   - 📝 Session name
   - 🌐 Hostname
   - 👤 Username
   - 🔒 Password (optional)
   - 🔑 SSH key file (optional)
   - 🔌 Port (default: 22)

### 💡 Quick Tips

- Press `F11` for fullscreen mode
- Use `Up/Down` arrows to navigate command history
- Press `Ctrl+L` to clear terminal
- Use `Ctrl+F` to search sessions

## 🔒 Security Features

- 🔐 All sensitive data is encrypted using Fernet encryption
- 🔑 Support for both password and SSH key authentication
- 🛡️ Secure storage of connection details
- 🔄 Automatic session timeout handling

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

If you encounter any issues or have questions, please:
1. Check the existing issues
2. Create a new issue with a detailed description
3. Include steps to reproduce the problem

---
Made with ❤️ by Owais Safa
