import React, { useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import {
  Button,
  Typography,
  Paper,
  Grid,
  Box,
  Snackbar,
  Alert,
  Tooltip,
  IconButton,
  List,
  Divider,
  TextField,
  Chip,
  CircularProgress, // Import CircularProgress
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import DonorReportsTable from "../DonorReportsTable/DonorReportsTable";
import ReportProgressBar from "../ReportProgressBar/ReportProgressBar";
import axios from "axios";

const Dashboard = () => {
  const [file, setFile] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [errorSnackbarOpen, setErrorSnackbarOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [taskGroupId, setTaskGroupId] = useState(null);
  const [refreshReportsTable, setRefreshReportsTable] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isGeneratingReports, setIsGeneratingReports] = useState(false); // Used to track loading

  const MAX_FILE_SIZE = 5 * 1024 * 1024;

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        ".xlsx",
      ],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    onDrop: (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        setErrorMessage(
          "Only Excel (.xlsx, .xls) and CSV (.csv) files are allowed."
        );
        setErrorSnackbarOpen(true);
        return;
      }

      const uploadedFile = acceptedFiles[0];
      if (uploadedFile.size > MAX_FILE_SIZE) {
        setErrorMessage("File size exceeds 5MB.");
        setErrorSnackbarOpen(true);
        return;
      }

      setFile(uploadedFile);
      setSuccessMessage("File validated and ready for upload!");
      setSnackbarOpen(true);
    },
    multiple: false,
  });

  useEffect(() => {
    const handleBeforeUnload = (event) => {
      if (isGeneratingReports) {
        const message =
          "Report generation is in progress. Are you sure you want to leave?";
        event.returnValue = message;
        return message;
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isGeneratingReports]);

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  const handleCloseErrorSnackbar = () => {
    setErrorSnackbarOpen(false);
  };

  const handleRemoveFile = () => {
    setFile(null);
    setSnackbarOpen(false);
  };

  const handleUploadFile = async () => {
    if (!file) return;

    setIsGeneratingReports(true); // Set loading state

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        "http://localhost:8000/api/reports/upload/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setTaskGroupId(response.data.task_group_id);
      setSuccessMessage(
        "File uploaded successfully! Report generation in progress."
      );
      setSnackbarOpen(true);
    } catch (error) {
      console.error(
        "Error uploading file:",
        error.response?.data?.error || error.message
      );
      setErrorMessage(error.response?.data?.error || "File upload failed.");
      setErrorSnackbarOpen(true);
    }
  };

  const handleReportCompletion = () => {
    setIsGeneratingReports(false); // Reset loading state when report generation completes
  };

  const refreshReports = () => {
    setRefreshReportsTable((prev) => !prev);
  };

  return (
    <Grid
      container
      direction="column"
      alignItems="center"
      justifyContent="center"
      style={{ minHeight: "100vh" }}
    >
      <Grid item>
        <Typography variant="h4" gutterBottom>
          Upload Excel File
        </Typography>
        <Paper
          elevation={3}
          style={{
            padding: 20,
            width: 400,
            textAlign: "center",
            border: "2px dashed grey",
            backgroundColor: isDragActive ? "#e0f7fa" : "#fff",
          }}
          {...getRootProps()}
        >
          <input {...getInputProps()} />
          {isDragActive ? (
            <Typography variant="body1">Drop the file here ...</Typography>
          ) : (
            <Typography variant="body1">
              {file ? (
                <>
                  Uploaded file: {file.name}
                  <Chip
                    label={`Size: ${(file.size / (1024 * 1024)).toFixed(2)} MB`}
                    color="primary"
                    variant="outlined"
                    style={{ marginLeft: "10px" }}
                  />
                </>
              ) : (
                "Drag & drop an Excel or CSV file here, or click to select one"
              )}
            </Typography>
          )}
        </Paper>

        {file && (
          <Box
            mt={2}
            display="flex"
            justifyContent="space-between"
            width="100%"
          >
            <Button
              variant="contained"
              color="primary"
              onClick={handleUploadFile}
              disabled={isGeneratingReports} // DISABLE BUTTON DURING UPLOAD
            >
              Generate Reports
            </Button>
            <Button variant="outlined" color="error" onClick={handleRemoveFile}>
              Remove File
            </Button>
          </Box>
        )}

        {/* Show the loading spinner while generating reports */}
        {isGeneratingReports && (
          <Box
            mt={2}
            display="flex"
            justifyContent="center"
            alignItems="center"
          >
            <CircularProgress />
            <Typography variant="body2" style={{ marginLeft: "10px" }}>
              Generating reports, this may take a moment...
            </Typography>
          </Box>
        )}

        {taskGroupId && (
          <ReportProgressBar
            taskGroupId={taskGroupId}
            onReportCompletion={handleReportCompletion} // Enable button on completion
          />
        )}

        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
        >
          <Alert onClose={handleCloseSnackbar} severity="success">
            {successMessage}
          </Alert>
        </Snackbar>

        <Snackbar
          open={errorSnackbarOpen}
          autoHideDuration={6000}
          onClose={handleCloseErrorSnackbar}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
        >
          <Alert onClose={handleCloseErrorSnackbar} severity="error">
            {errorMessage}
          </Alert>
        </Snackbar>
      </Grid>

      <Grid item style={{ width: "80%", marginTop: 40 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h5" gutterBottom>
            Donor Reports
          </Typography>
          <Box display="flex" alignItems="center">
            <TextField
              label="Search by name"
              variant="outlined"
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ marginRight: "0.5rem" }}
            />
            <IconButton color="primary" onClick={refreshReports}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </Box>

        <DonorReportsTable
          refreshTrigger={refreshReportsTable}
          searchQuery={searchQuery}
        />
      </Grid>
    </Grid>
  );
};

export default Dashboard;
