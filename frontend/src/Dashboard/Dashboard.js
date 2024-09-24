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
  ListItem,
  ListItemText,
  Divider,
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import axios from "axios";

const Dashboard = () => {
  const [file, setFile] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [errorSnackbarOpen, setErrorSnackbarOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

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
      console.log(response.data.message);
      alert("File uploaded successfully: " + response.data.message);
    } catch (error) {
      console.error(
        "Error uploading file:",
        error.response?.data?.error || error.message
      );
      setErrorMessage(error.response?.data?.error || "File upload failed.");
      setErrorSnackbarOpen(true);
    }
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
              Generate Report
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
                <List dense>
                  <ListItem>
                    <ListItemText primary="Donor ID" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Donation ID" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Donor First Name" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Donor Last Name" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Donor Email" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Donation Amount" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Charity" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Cause ID" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Cause" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Date of Donation" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Time of Donation" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Phone Number" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Address" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Payment Type" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Recurrence Status" />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Tax Receipt Status" />
                  </ListItem>
                </List>
              </>
            }
          >
            <IconButton>
              <InfoOutlinedIcon />
            </IconButton>
          </Tooltip>
        </Box>

        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
        >
          <Alert onClose={handleCloseSnackbar} severity="success">
            File uploaded successfully!
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
    </Grid>
  );
};

export default Dashboard;
