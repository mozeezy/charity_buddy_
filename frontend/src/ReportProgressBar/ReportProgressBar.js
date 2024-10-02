import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import LinearProgress from "@mui/material/LinearProgress";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

const ReportProgressBar = ({ taskIds }) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("PENDING");
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      fetchTaskStatus();
    }, 2000);

    return () => clearInterval(intervalRef.current);
  }, [taskIds]);

  const fetchTaskStatus = async () => {
    try {
      const taskStatuses = await Promise.all(
        taskIds.map((taskId) =>
          axios.get(`http://localhost:8000/api/reports/status/${taskId}/`)
        )
      );

      let totalProgress = 0;
      let completedTasks = 0;

      taskStatuses.forEach((response) => {
        const { status, progress } = response.data;
        totalProgress += progress;

        if (status === "SUCCESS" || status === "FAILED") {
          completedTasks += 1;
        }
      });

      const overallProgress = Math.round(totalProgress / taskIds.length);
      setProgress(overallProgress);

      if (completedTasks === taskIds.length) {
        setSnackbarOpen(true);
        clearInterval(intervalRef.current);
        setStatus("COMPLETED");
      }
    } catch (error) {
      console.error("Error fetching task status:", error);
    }
  };

  return (
    <Box mt={2} width="100%">
      <LinearProgress variant="determinate" value={progress} />
      <Typography variant="body2" color="textSecondary" align="center" mt={1}>
        {progress}% Complete
      </Typography>
      {status === "COMPLETED" && (
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={() => setSnackbarOpen(false)}
          anchorOrigin={{ vertical: "top", horizontal: "right" }} // Dock Snackbar to the top right
        >
          <Alert severity="success" onClose={() => setSnackbarOpen(false)}>
            Report generation completed successfully!
          </Alert>
        </Snackbar>
      )}
    </Box>
  );
};

export default ReportProgressBar;
