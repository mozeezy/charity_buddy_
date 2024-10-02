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
import Pagination from "@mui/material/Pagination";
import Box from "@mui/material/Box";

const DonorReportsTable = ({ refreshTrigger, searchQuery }) => {
  const [donorReports, setDonorReports] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchDonorReports(page, searchQuery);
  }, [page, refreshTrigger, searchQuery]); // Add searchQuery to the dependency array

  const fetchDonorReports = async (page, searchQuery) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/reports/donor-reports-list/?page=${page}&search=${searchQuery}`
      );

      setDonorReports(response.data.results);
      setTotalPages(Math.ceil(response.data.count / 10));
    } catch (error) {
      console.error("Error fetching donor reports:", error);
    }
  };

  const handleDownload = (reportUrl) => {
    const link = document.createElement("a");
    link.href = reportUrl;
    link.download = reportUrl.split("/").pop();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePageChange = (event, value) => {
    setPage(value);
  };

  return (
    <Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead style={{ backgroundColor: "#f5f5f5" }}>
            <TableRow>
              <TableCell>
                <b>Full Name</b>
              </TableCell>
              <TableCell>
                <b>Donor ID</b>
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

      <Box display="flex" justifyContent="center" mt={2}>
        <Pagination
          count={totalPages}
          page={page}
          onChange={handlePageChange}
          color="primary"
        />
      </Box>
    </Box>
  );
};

export default DonorReportsTable;
