import React, { useState, useEffect } from "react";
import axios from "axios";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import IconButton from "@mui/material/IconButton";
import DownloadIcon from "@mui/icons-material/Download";
import Checkbox from "@mui/material/Checkbox";
import Button from "@mui/material/Button";
import Pagination from "@mui/material/Pagination";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert"; 

const DonorReportsTable = ({ refreshTrigger, searchQuery }) => {
  const [donorReports, setDonorReports] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalReports, setTotalReports] = useState([]);
  const [sortBy, setSortBy] = useState("full_name");
  const [sortOrder, setSortOrder] = useState("asc");
  const [selectedReports, setSelectedReports] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  const [loading, setLoading] = useState(false); 
  const [errorSnackbarOpen, setErrorSnackbarOpen] = useState(false); 
  const [errorMessage, setErrorMessage] = useState(""); 

  useEffect(() => {
    fetchDonorReports(page, searchQuery, sortBy, sortOrder);
  }, [page, refreshTrigger, searchQuery, sortBy, sortOrder]);

  useEffect(() => {
    fetchAllReports(); 
  }, []);

  const fetchDonorReports = async (page, searchQuery, sortBy, sortOrder) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/reports/donor-reports-list/?page=${page}&search=${searchQuery}&sort_by=${sortBy}&sort_order=${sortOrder}`
      );
      setDonorReports(response.data.results);
      setTotalPages(Math.ceil(response.data.count / 10));
    } catch (error) {
      console.error("Error fetching donor reports:", error);
    }
  };

  const fetchAllReports = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/reports/all-reports-urls/?search=${searchQuery}`
      );
      setTotalReports(response.data);
    } catch (error) {
      console.error("Error fetching all reports:", error);
    }
  };

  const handleDownload = (reportUrl) => {
    const link = document.createElement("a");
    link.href = reportUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePageChange = (event, value) => {
    setPage(value);
  };

  const handleSortChange = (field) => {
    setSortBy(field);
    setSortOrder(sortOrder === "asc" ? "desc" : "asc");
  };

  const handleSelect = (reportUrl) => {
    if (selectedReports.includes(reportUrl)) {
      setSelectedReports(selectedReports.filter((url) => url !== reportUrl));
    } else {
      setSelectedReports([...selectedReports, reportUrl]);
    }
  };

  const handleSelectAll = async () => {
    if (!selectAll) {
      if (totalReports.length === 0) {
        await fetchAllReports();
      }
      const allReportUrls = totalReports.map((report) => report.report_url);
      setSelectedReports(allReportUrls);
    } else {
      setSelectedReports([]);
    }
    setSelectAll(!selectAll);
  };

  const isReportSelected = (reportUrl) => selectedReports.includes(reportUrl);

  const handleBulkDownload = async () => {
    try {
      setLoading(true); // Show loader
      const response = await axios.post(
        "http://localhost:8000/api/reports/download-zip/",
        { report_urls: selectedReports },
        {
          responseType: "blob", 
        }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "reports.zip"); 
      document.body.appendChild(link);
      link.click();
    } catch (error) {
      setErrorMessage("Error creating ZIP file: " + error.message); 
      setErrorSnackbarOpen(true); 
    } finally {
      setLoading(false); 
    }
  };

  const handleCloseErrorSnackbar = () => {
    setErrorSnackbarOpen(false);
  };

  return (
    <Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead style={{ backgroundColor: "#f5f5f5" }}>
            <TableRow>
              <TableCell>
                <Checkbox
                  checked={selectAll}
                  onChange={handleSelectAll}
                  inputProps={{ "aria-label": "select all reports" }}
                />
              </TableCell>
              <TableCell>
                <b
                  onClick={() => handleSortChange("full_name")}
                  style={{ cursor: "pointer" }}
                >
                  Full Name{" "}
                  {sortBy === "full_name" && (sortOrder === "asc" ? "▲" : "▼")}
                </b>
              </TableCell>
              <TableCell>
                <b
                  onClick={() => handleSortChange("donor_id")}
                  style={{ cursor: "pointer" }}
                >
                  Donor ID{" "}
                  {sortBy === "donor_id" && (sortOrder === "asc" ? "▲" : "▼")}
                </b>
              </TableCell>
              <TableCell>
                <b>Email</b>
              </TableCell>
              <TableCell>
                <b>Download Report</b>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {donorReports.map((donor, index) => (
              <TableRow key={index}>
                <TableCell>
                  <Checkbox
                    checked={isReportSelected(donor.report_url)}
                    onChange={() => handleSelect(donor.report_url)}
                    inputProps={{
                      "aria-label": `select report for ${donor.full_name}`,
                    }}
                  />
                </TableCell>
                <TableCell>{donor.full_name}</TableCell>
                <TableCell>{donor.donor_id}</TableCell>
                <TableCell>{donor.email}</TableCell>
                <TableCell>
                  <IconButton
                    onClick={() => handleDownload(donor.report_url)}
                    aria-label="download"
                  >
                    <DownloadIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <Box display="flex" justifyContent="center" mt={2}>
        <Pagination
          count={totalPages}
          page={page}
          onChange={handlePageChange}
          color="primary"
        />
      </Box>

      {/* Bulk Download Button */}
      {selectedReports.length > 0 && (
        <Box display="flex" justifyContent="center" mt={2}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleBulkDownload}
            disabled={loading} // Disable button when loading
          >
            {loading ? (
              <CircularProgress size={24} />
            ) : (
              `Download Selected Reports (${selectedReports.length})`
            )}
          </Button>
        </Box>
      )}

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
    </Box>
  );
};

export default DonorReportsTable;
