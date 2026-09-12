import React, { useState, useEffect, useCallback } from 'react'
import {
  AppBar, Toolbar, Typography, Container, Grid, Paper, Box, Button, TextField,
  Select, MenuItem, FormControl, InputLabel, Chip, Table, TableBody, TableCell,
  TableHead, TableRow, Alert, CircularProgress, Divider, Card, CardContent,
  ToggleButton, ToggleButtonGroup, IconButton, Tooltip,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import WarningIcon from '@mui/icons-material/Warning'
import ErrorIcon from '@mui/icons-material/Error'
import { setApiKey, submitApplication, getApplication, listApplications, getHealth } from './api'
import { VARIANTS, API_KEYS } from './sampleData'

const STATUS_COLORS = {
  APPROVED: 'success',
  REJECTED: 'error',
  REVIEW: 'warning',
  PROCESSING: 'info',
  FAILED: 'error',
}

const STATUS_ICONS = {
  APPROVED: <CheckCircleIcon />,
  REJECTED: <CancelIcon />,
  REVIEW: <WarningIcon />,
  PROCESSING: <CircularProgress size={16} />,
  FAILED: <ErrorIcon />,
}

const CLAUSE_STATUS_COLORS = {
  passed: 'success',
  failed: 'error',
  undetermined: 'default',
}

function App() {
  const [customer, setCustomer] = useState('kaveri')
  const [variant, setVariant] = useState('sample')
  const [applications, setApplications] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [health, setHealth] = useState(null)
  const [idempotencyKey, setIdempotencyKey] = useState('')

  useEffect(() => {
    setApiKey(API_KEYS[customer])
    loadApplications()
    loadHealth()
  }, [customer])

  const loadApplications = useCallback(async () => {
    try {
      const data = await listApplications()
      setApplications(data)
    } catch (e) {
      console.error(e)
    }
  }, [customer])

  const loadHealth = async () => {
    try {
      const data = await getHealth()
      setHealth(data)
    } catch (e) {
      setHealth({ status: 'unreachable' })
    }
  }

  const loadDetail = async (id) => {
    setSelected(id)
    setLoading(true)
    try {
      const data = await getApplication(id)
      setDetail(data)
      if (data.status === 'PROCESSING') {
        setTimeout(() => loadDetail(id), 2000)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = VARIANTS[variant].data
      const result = await submitApplication(data, idempotencyKey || undefined)
      await loadApplications()
      loadDetail(result.application_id)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const formatInr = (n) => n ? `₹${(n / 100000).toFixed(2)}L` : '—'

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f7fafc' }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: '#1a365d' }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            Deepvue Risk Decisioning
          </Typography>
          {health && (
            <Chip
              label={`System: ${health.status}`}
              color={health.status === 'healthy' ? 'success' : 'warning'}
              size="small"
              sx={{ mr: 2 }}
            />
          )}
          <ToggleButtonGroup
            value={customer}
            exclusive
            onChange={(_, v) => v && setCustomer(v)}
            size="small"
            sx={{ bgcolor: 'rgba(255,255,255,0.1)' }}
          >
            <ToggleButton value="kaveri" sx={{ color: 'white', '&.Mui-selected': { bgcolor: 'rgba(255,255,255,0.2)' } }}>
              Kaveri Capital
            </ToggleButton>
            <ToggleButton value="nexa" sx={{ color: 'white', '&.Mui-selected': { bgcolor: 'rgba(255,255,255,0.2)' } }}>
              Nexa Finserv
            </ToggleButton>
          </ToggleButtonGroup>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

        <Grid container spacing={3}>
          {/* Submit Form */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom fontWeight={600}>Submit Application</Typography>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Sample Variant</InputLabel>
                <Select value={variant} label="Sample Variant" onChange={(e) => setVariant(e.target.value)}>
                  {Object.entries(VARIANTS).map(([key, v]) => (
                    <MenuItem key={key} value={key}>{v.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Idempotency Key (optional)"
                value={idempotencyKey}
                onChange={(e) => setIdempotencyKey(e.target.value)}
                sx={{ mb: 2 }}
                size="small"
              />
              <Button
                variant="contained"
                fullWidth
                onClick={handleSubmit}
                disabled={loading}
                sx={{ py: 1.5 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Submit Application'}
              </Button>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Policy: {customer === 'kaveri' ? 'Kaveri Capital' : 'Nexa Finserv'}
              </Typography>
            </Paper>

            {/* Applications List */}
            <Paper sx={{ p: 2, mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={600}>Recent Applications</Typography>
                <IconButton size="small" onClick={loadApplications}><RefreshIcon /></IconButton>
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Business</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {applications.map((app) => (
                    <TableRow
                      key={app.application_id}
                      hover
                      selected={selected === app.application_id}
                      onClick={() => loadDetail(app.application_id)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell sx={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {app.business_name}
                      </TableCell>
                      <TableCell>
                        <Chip label={app.status} color={STATUS_COLORS[app.status] || 'default'} size="small" />
                      </TableCell>
                    </TableRow>
                  ))}
                  {applications.length === 0 && (
                    <TableRow><TableCell colSpan={2} align="center">No applications yet</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </Paper>
          </Grid>

          {/* Decision Detail */}
          <Grid item xs={12} md={8}>
            {detail ? (
              <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  {STATUS_ICONS[detail.status]}
                  <Box>
                    <Typography variant="h5" fontWeight={700}>{detail.status}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {detail.policy_id} v{detail.policy_version} · {detail.application_id.slice(0, 8)}...
                    </Typography>
                  </Box>
                  {detail.decision?.degraded && (
                    <Chip label="DEGRADED" color="warning" size="small" />
                  )}
                </Box>

                {detail.status === 'PROCESSING' && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Processing in background — auto-refreshing...
                  </Alert>
                )}

                {detail.decision && (
                  <>
                    <Typography variant="h6" fontWeight={600} gutterBottom>Policy Reasons</Typography>
                    {detail.decision.reasons?.map((r, i) => (
                      <Card key={i} variant="outlined" sx={{ mb: 1 }}>
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Chip label={r.clause_id} size="small" variant="outlined" />
                            <Chip label={r.status} color={CLAUSE_STATUS_COLORS[r.status]} size="small" />
                          </Box>
                          <Typography variant="body2" color="text.secondary">{r.clause_text}</Typography>
                          <Typography variant="body2" sx={{ mt: 0.5 }}>{r.reason}</Typography>
                        </CardContent>
                      </Card>
                    ))}

                    <Divider sx={{ my: 3 }} />

                    <Typography variant="h6" fontWeight={600} gutterBottom>Upstream Calls</Typography>
                    {detail.upstream_calls?.map((call, i) => (
                      <Card key={i} variant="outlined" sx={{ mb: 1 }}>
                        <CardContent sx={{ py: 1.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip
                              label={call.success ? 'SUCCESS' : 'FAILED'}
                              color={call.success ? 'success' : 'error'}
                              size="small"
                            />
                            <Typography variant="body2">{call.endpoint}</Typography>
                          </Box>
                          {call.attempts?.map((a, j) => (
                            <Typography key={j} variant="caption" color="text.secondary" display="block">
                              Attempt {a.attempt}: {a.status_code || a.error || 'pending'}
                              {a.retry_after && ` (retry after ${a.retry_after}s)`}
                            </Typography>
                          ))}
                          {call.data && (
                            <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                              Turnover: {formatInr(call.data.annual_turnover_inr)} ·
                              Inc: {call.data.incorporation_date} ·
                              GST: {call.data.gstin_status}
                            </Typography>
                          )}
                        </CardContent>
                      </Card>
                    ))}

                    <Divider sx={{ my: 3 }} />

                    <Typography variant="h6" fontWeight={600} gutterBottom>Extracted Fields</Typography>
                    {detail.extraction?.fields && Object.entries(detail.extraction.fields).map(([key, field]) => (
                      <Card key={key} variant="outlined" sx={{ mb: 1 }}>
                        <CardContent sx={{ py: 1.5 }}>
                          <Typography variant="subtitle2" fontWeight={600}>{key}</Typography>
                          <Typography variant="body2">
                            {typeof field === 'object' && !Array.isArray(field)
                              ? field.value || JSON.stringify(field.normalized_inr || field)
                              : JSON.stringify(field)}
                          </Typography>
                          {field.provenance && (
                            <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                              "{field.provenance.quote?.slice(0, 80)}..."
                            </Typography>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                    {detail.extraction?.concerns?.map((c, i) => (
                      <Alert key={i} severity="warning" sx={{ mb: 1 }}>
                        <strong>{c.type}:</strong> {c.description}
                      </Alert>
                    ))}
                    {detail.extraction?.extraction_degraded && (
                      <Alert severity="info">Extraction was degraded — unstructured material could not be fully read</Alert>
                    )}
                  </>
                )}
              </Paper>
            ) : (
              <Paper sx={{ p: 6, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  Submit an application or select one from the list to view its decision
                </Typography>
              </Paper>
            )}
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}

export default App
