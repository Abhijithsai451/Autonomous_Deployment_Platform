import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './index.css'; // Add standard Tailwind directives here

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);