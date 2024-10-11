import React, { useState, useEffect } from "react";
import LinearProgress from "@mui/material/LinearProgress";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

const ReportProgressBar = ({ taskGroupId }) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("PENDING");
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  useEffect(() => {
    if (!taskGroupId) return;

    const socket = new WebSocket(
      `ws://localhost:8000/ws/reports/progress/${taskGroupId}/`
    );

    socket.onopen = () => {
      console.log("WebSocket connection established.");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      const roundedProgress = Math.round(data.progress);

      setProgress(roundedProgress);
      setStatus(data.status);

      if (data.status === "SUCCESS" || data.status === "FAILED") {
        setSnackbarOpen(true);
        socket.close();
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [taskGroupId]);

  return (
    <Box mt={2} width="100%">
      <LinearProgress variant="determinate" value={progress} />
      <Typography variant="body2" color="textSecondary" align="center">
        {progress}% completed
      </Typography>
      {status === "SUCCESS" && (
        <Snackbar open={snackbarOpen} autoHideDuration={6000}>
          <Alert severity="success">
            Report generation completed successfully!
          </Alert>
        </Snackbar>
      )}
      {status === "FAILED" && (
        <Snackbar open={snackbarOpen} autoHideDuration={6000}>
          <Alert severity="error">Report generation failed.</Alert>
        </Snackbar>
      )}
    </Box>
  );
};

export default ReportProgressBar;
