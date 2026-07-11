import { useEffect, useRef, useState } from 'react'
import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import DeleteSweepRoundedIcon from '@mui/icons-material/DeleteSweepRounded'
import DirectionsBikeRoundedIcon from '@mui/icons-material/DirectionsBikeRounded'
import SendRoundedIcon from '@mui/icons-material/SendRounded'
import SmartToyRoundedIcon from '@mui/icons-material/SmartToyRounded'
import TravelExploreRoundedIcon from '@mui/icons-material/TravelExploreRounded'
import { Alert, Avatar, Box, Button, Card, CardContent, CircularProgress, Divider, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { activitiesApi, chatApi, type AIDataBasis, type ChatHistoryItem, type ChatSource } from '../api'
import { useAuth } from '../auth/AuthContext'
import { AIDataBasisPanel } from '../components/AIDataBasisPanel'
import { PageHeader } from '../components/PageHeader'
import { errorMessage, formatDate } from '../utils/format'

interface ChatUiMessage extends ChatHistoryItem {
  id: string
  sources?: ChatSource[]
  toolsUsed?: string[]
  provider?: string
  dataBasis?: AIDataBasis | null
}

const quickPrompts = [
  'Wie hat sich meine Ausdauer in den letzten drei Monaten entwickelt?',
  'Welche war meine beste Grundlagenausdauer-Einheit?',
  'Bei welcher schnellen Fahrt hatte ich besonders viel Gegenwind?',
  'Was sollte ich als Nächstes trainieren?',
]

function messageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function welcomeMessage(): ChatUiMessage {
  return {
    id: 'welcome',
    role: 'assistant',
    content: 'Hallo! Ich bin dein Avento Coach. Frag mich nach deiner Fitnessentwicklung, einzelnen Fahrten, Herzfrequenz, Wetter oder Trainingsideen. Ich suche die passenden Daten gezielt für dich heraus.',
  }
}

function loadHistory(key: string): ChatUiMessage[] {
  try {
    const stored = localStorage.getItem(key)
    if (!stored) return [welcomeMessage()]
    const parsed = JSON.parse(stored) as ChatUiMessage[]
    return Array.isArray(parsed) && parsed.length ? parsed : [welcomeMessage()]
  } catch {
    return [welcomeMessage()]
  }
}

const toolLabels: Record<string, string> = {
  list_activities: 'Aktivitäten durchsucht',
  search_activities: 'Aktivitäten durchsucht',
  get_activity: 'Fahrtdetails geladen',
  get_activity_details: 'Fahrtdetails geladen',
  get_activity_track: 'Streckendaten analysiert',
  find_similar_activities: 'Ähnliche Fahrten gesucht',
  compare_activities: 'Fahrten verglichen',
  get_statistics: 'Statistik ausgewertet',
  get_training_statistics: 'Statistik ausgewertet',
  get_weather: 'Wetter geprüft',
  get_splits: 'Kilometerabschnitte geprüft',
  analyze_route_segment: 'Streckenabschnitt analysiert',
}

export function ChatPage() {
  const { profile } = useAuth()
  const storageKey = `avento.chat.history.${profile?.id ?? 'local'}`
  const [messages, setMessages] = useState<ChatUiMessage[]>(() => loadHistory(storageKey))
  const [input, setInput] = useState('')
  const [activityId, setActivityId] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const activities = useQuery({ queryKey: ['activities', 'chat-picker'], queryFn: () => activitiesApi.list({ limit: 50 }) })
  const chat = useMutation({
    mutationFn: ({ message, history, focusId }: { message: string; history: ChatHistoryItem[]; focusId?: string }) => chatApi.send(message, history, focusId),
    onSuccess: (response) => {
      setMessages((current) => [...current, {
        id: messageId(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        toolsUsed: response.tools_used,
        provider: response.provider,
        dataBasis: response.data_basis,
      }])
    },
  })

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(messages.slice(-50)))
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages, storageKey])

  function submit(text = input) {
    const message = text.trim()
    if (!message || chat.isPending) return
    const history = messages.slice(-20).map(({ role, content }) => ({ role, content }))
    setMessages((current) => [...current, { id: messageId(), role: 'user', content: message }])
    setInput('')
    chat.reset()
    chat.mutate({ message, history, focusId: activityId || undefined })
  }

  function clearHistory() {
    setMessages([welcomeMessage()])
    setInput('')
    chat.reset()
  }

  return (
    <>
      <PageHeader
        eyebrow="DEIN PERSÖNLICHER COACH"
        title="Avento Chat"
        description="Sprich mit deinen gesamten Trainingsdaten. Der Coach kann Aktivitäten, Strecken, Kilometerwerte, Herzfrequenz und Wetter gezielt abrufen."
        action={<Button color="inherit" startIcon={<DeleteSweepRoundedIcon />} onClick={clearHistory} disabled={messages.length <= 1}>Verlauf leeren</Button>}
      />

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 1fr) 320px' }, gap: 2.5, alignItems: 'start' }}>
        <Card sx={{ overflow: 'hidden' }}>
          <Box sx={{ height: { xs: 'min(58vh, 600px)', md: 'min(64vh, 680px)' }, minHeight: 430, overflowY: 'auto', p: { xs: 2, sm: 3 }, bgcolor: 'rgba(var(--mui-palette-background-defaultChannel) / .55)' }} aria-live="polite">
            <Stack spacing={2.25}>
              {messages.map((message) => <ChatBubble key={message.id} message={message} profileName={profile?.display_name} avatar={profile?.avatar_data_url} />)}
              {chat.isPending && (
                <Stack direction="row" gap={1.25} alignItems="flex-start">
                  <Avatar sx={{ width: 36, height: 36, bgcolor: 'primary.main' }}><SmartToyRoundedIcon fontSize="small" /></Avatar>
                  <Box sx={{ px: 2, py: 1.5, bgcolor: 'background.paper', borderRadius: '4px 18px 18px 18px', border: '1px solid', borderColor: 'divider' }}>
                    <Stack direction="row" alignItems="center" gap={1}><CircularProgress size={18} /><Typography variant="body2" color="text.secondary">Ich durchsuche deine Trainingsdaten …</Typography></Stack>
                  </Box>
                </Stack>
              )}
              <div ref={endRef} />
            </Stack>
          </Box>
          <Divider />
          <Box component="form" onSubmit={(event) => { event.preventDefault(); submit() }} sx={{ p: { xs: 1.5, sm: 2 }, bgcolor: 'background.paper' }}>
            {chat.isError && <Alert severity="error" sx={{ mb: 1.5 }}>{errorMessage(chat.error)}</Alert>}
            <Stack direction="row" gap={1} alignItems="flex-end">
              <TextField
                fullWidth
                multiline
                maxRows={5}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }}
                placeholder="Was möchtest du über dein Training wissen?"
                aria-label="Nachricht an Avento Chat"
              />
              <Button type="submit" variant="contained" aria-label="Nachricht senden" disabled={!input.trim() || chat.isPending} sx={{ minWidth: 48, width: 48, px: 0 }}><SendRoundedIcon /></Button>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>Enter sendet · Umschalt + Enter fügt eine neue Zeile ein</Typography>
          </Box>
        </Card>

        <Stack spacing={2.5}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" gap={1}><DirectionsBikeRoundedIcon color="primary" /><Typography variant="h3">Fokusfahrt</Typography></Stack>
              <Typography variant="body2" color="text.secondary" sx={{ my: 1.5 }}>Optional kannst du eine konkrete Fahrt als Ausgangspunkt setzen.</Typography>
              <TextField select fullWidth label="Aktivität" value={activityId} onChange={(event) => setActivityId(event.target.value)} disabled={activities.isLoading || activities.isError}>
                <MenuItem value="">Alle Trainingsdaten</MenuItem>
                {activities.data?.items.map((activity) => <MenuItem key={activity.id} value={activity.id}>{activity.title} · {formatDate(activity.started_at)}</MenuItem>)}
              </TextField>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" gap={1}><AutoAwesomeRoundedIcon color="primary" /><Typography variant="h3">Ideen zum Fragen</Typography></Stack>
              <Stack spacing={1} sx={{ mt: 1.5 }}>
                {quickPrompts.map((prompt) => <Button key={prompt} variant="outlined" color="inherit" onClick={() => submit(prompt)} disabled={chat.isPending} sx={{ justifyContent: 'flex-start', textAlign: 'left', height: 'auto', py: 1.1 }}>{prompt}</Button>)}
              </Stack>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" gap={1}><TravelExploreRoundedIcon color="primary" /><Typography variant="h3">Nachvollziehbar</Typography></Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1.25, lineHeight: 1.65 }}>Antworten verlinken die verwendeten Fahrten und zeigen, welche Datenwerkzeuge eingesetzt wurden. So kannst du jede Aussage direkt prüfen.</Typography>
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </>
  )
}

function ChatBubble({ message, profileName, avatar }: { message: ChatUiMessage; profileName?: string; avatar?: string | null }) {
  const user = message.role === 'user'
  return (
    <Stack direction={user ? 'row-reverse' : 'row'} gap={1.25} alignItems="flex-start">
      <Avatar src={user ? avatar ?? undefined : undefined} sx={{ width: 36, height: 36, bgcolor: user ? 'secondary.light' : 'primary.main', color: user ? 'secondary.dark' : 'white', fontWeight: 800 }}>
        {user ? profileName?.charAt(0).toUpperCase() : <SmartToyRoundedIcon fontSize="small" />}
      </Avatar>
      <Box sx={{ maxWidth: { xs: 'calc(100% - 52px)', sm: '80%' } }}>
        <Box sx={{ px: 2, py: 1.5, bgcolor: user ? 'primary.main' : 'background.paper', color: user ? 'primary.contrastText' : 'text.primary', borderRadius: user ? '18px 4px 18px 18px' : '4px 18px 18px 18px', border: user ? 'none' : '1px solid', borderColor: 'divider', boxShadow: user ? 'none' : '0 8px 24px rgba(20,50,45,.05)' }}>
          <ChatText content={message.content} />
        </Box>
        {!user && message.provider && (
          <Box sx={{ mt: 1.1 }}>
            <AIDataBasisPanel
              dataBasis={message.dataBasis}
              sources={message.sources}
              tools={message.toolsUsed}
              toolLabels={toolLabels}
              provider={message.provider}
              defaultExpanded
            />
          </Box>
        )}
      </Box>
    </Stack>
  )
}

function ChatText({ content }: { content: string }) {
  return (
    <Stack spacing={.75}>
      {content.split(/\r?\n/).map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) return <Box key={index} sx={{ height: .35 }} />
        const isListItem = /^[-*]\s+/.test(trimmed) || /^\d+[.)]\s+/.test(trimmed)
        const text = trimmed.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, '')
        return (
          <Box key={index} component={isListItem ? 'li' : 'div'} sx={isListItem ? { ml: 2, pl: .5 } : undefined}>
            <Typography component="span" sx={{ lineHeight: 1.7 }}>{renderInlineMarkdown(text)}</Typography>
          </Box>
        )
      })}
    </Stack>
  )
}

function renderInlineMarkdown(value: string) {
  return value.split(/(\*\*[^*]+\*\*)/g).map((part, index) => (
    part.startsWith('**') && part.endsWith('**')
      ? <Box component="strong" key={index} sx={{ fontWeight: 800 }}>{part.slice(2, -2)}</Box>
      : <span key={index}>{part}</span>
  ))
}
