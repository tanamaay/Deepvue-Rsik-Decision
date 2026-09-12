import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material'
import App from './App'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1a365d' },
    secondary: { main: '#2b6cb0' },
    success: { main: '#276749' },
    warning: { main: '#c05621' },
    error: { main: '#c53030' },
  },
  typography: { fontFamily: 'Inter, sans-serif' },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <App />
  </ThemeProvider>
)
