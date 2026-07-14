import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { profileApi, type HeartRateZone } from '../../../api'
import { useAuth } from '../../../auth/AuthContext'

interface ProfileControllerValue {
  name: string
  setName: React.Dispatch<React.SetStateAction<string>>
  hrMax: number | ''
  setHrMax: React.Dispatch<React.SetStateAction<number | ''>>
  hrRest: number | ''
  setHrRest: React.Dispatch<React.SetStateAction<number | ''>>
  zones: HeartRateZone[]
  setZones: React.Dispatch<React.SetStateAction<HeartRateZone[]>>
  trainingGoals: string[]
  setTrainingGoals: React.Dispatch<React.SetStateAction<string[]>>
  totpCode: string
  setTotpCode: React.Dispatch<React.SetStateAction<string>>
  passkeyName: string
  setPasskeyName: React.Dispatch<React.SetStateAction<string>>
  currentPassword: string
  setCurrentPassword: React.Dispatch<React.SetStateAction<string>>
  newPassword: string
  setNewPassword: React.Dispatch<React.SetStateAction<string>>
  passwordConfirmation: string
  setPasswordConfirmation: React.Dispatch<React.SetStateAction<string>>
  save: ReturnType<typeof useProfileSaveMutation>
}

const ProfileControllerContext = createContext<ProfileControllerValue | null>(null)

function useProfileSaveMutation(name: string, hrMax: number | '', hrRest: number | '', zones: HeartRateZone[], trainingGoals: string[]) {
  const { setProfile } = useAuth()
  return useMutation({
    mutationFn: () => profileApi.update({ display_name: name.trim(), hr_max: hrMax === '' ? null : Number(hrMax), hr_rest: hrRest === '' ? null : Number(hrRest), hr_zones: zones, training_goals: trainingGoals }),
    onSuccess: setProfile,
  })
}

export function ProfileControllerProvider({ children }: { children: React.ReactNode }) {
  const { profile } = useAuth()
  const [name, setName] = useState(profile?.display_name ?? '')
  const [hrMax, setHrMax] = useState<number | ''>(profile?.hr_max ?? '')
  const [hrRest, setHrRest] = useState<number | ''>(profile?.hr_rest ?? '')
  const [zones, setZones] = useState<HeartRateZone[]>(profile?.hr_zones ?? [])
  const [trainingGoals, setTrainingGoals] = useState<string[]>(profile?.training_goals ?? [])
  const [totpCode, setTotpCode] = useState('')
  const [passkeyName, setPasskeyName] = useState('Mein Passkey')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const save = useProfileSaveMutation(name, hrMax, hrRest, zones, trainingGoals)

  // Synchronisiere erst bei einem Kontowechsel oder nach erfolgreichem Speichern.
  // Ein reiner Wechsel der Darstellungsvariante lässt lokale Entwürfe unangetastet.
  useEffect(() => {
    if (!profile) return
    setName(profile.display_name)
    setHrMax(profile.hr_max ?? '')
    setHrRest(profile.hr_rest ?? '')
    setZones(profile.hr_zones)
    setTrainingGoals(profile.training_goals ?? [])
  }, [profile?.id, save.data])

  const value = useMemo(() => ({
    name, setName, hrMax, setHrMax, hrRest, setHrRest, zones, setZones,
    trainingGoals, setTrainingGoals, totpCode, setTotpCode, passkeyName,
    setPasskeyName, currentPassword, setCurrentPassword, newPassword,
    setNewPassword, passwordConfirmation, setPasswordConfirmation, save,
  }), [name, hrMax, hrRest, zones, trainingGoals, totpCode, passkeyName, currentPassword, newPassword, passwordConfirmation, save])
  return <ProfileControllerContext.Provider value={value}>{children}</ProfileControllerContext.Provider>
}

export function useProfileController() {
  const context = useContext(ProfileControllerContext)
  if (!context) throw new Error('useProfileController muss innerhalb des ProfileControllerProvider verwendet werden.')
  return context
}
