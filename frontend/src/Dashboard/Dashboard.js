import React, { useState } from "react";
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
  const [taskId, setTaskId] = useState(null);
  const [refreshReportsTable, setRefreshReportsTable] = useState(false); // State to trigger refresh
  const [searchQuery, setSearchQuery] = useState(""); // State for search query

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

      setTaskId(response.data.task_ids);
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

  // Function to refresh the reports table
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
              {file
                ? `Uploaded file: ${file.name}`
                : "Drag & drop an Excel or CSV file here, or click to select one"}
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
              disabled={!file}
            >
              Generate Reports
            </Button>
            <Button variant="outlined" color="error" onClick={handleRemoveFile}>
              Remove File
            </Button>
          </Box>
        )}

        <Box mt={2} display="flex" alignItems="center" justifyContent="center">
          <Tooltip
            title={
              <>
                <Typography variant="subtitle1" gutterBottom>
                  Please upload a file with the following columns:
                </Typography>
                <Divider />
                <List dense>{/* List of columns */}</List>
              </>
            }
          >
            <IconButton>
              <InfoOutlinedIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {taskId && <ReportProgressBar taskIds={taskId} />}

        {/* Success Snackbar */}
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

        {/* Error Snackbar */}
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
            {/* Search Bar */}
            <TextField
              label="Search by name"
              variant="outlined"
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ marginRight: "0.5rem" }} // Space between search and refresh
            />
            {/* Refresh Button */}
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
