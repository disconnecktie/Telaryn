// Protect Telaryn's user-visible workflows while components and ownership evolve.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import App from './App'
import {
  acceptAIReview,
  createAcceptanceCriterion,
  createAIReview,
  createProject,
  createSubtask,
  createTicket,
  createTicketUpdate,
  getAcceptanceCriteria,
  getCurrentSession,
  getCurrentWorkIntake,
  getDeploymentAdministratorAccess,
  getFeedbackReviewerAccess,
  getFeedbackQueue,
  getIntakeReviewerAccess,
  getPreferences,
  getOnboarding,
  getReportProjects,
  savePreferences,
  getProjects,
  getMyWork,
  getProjectWorkOverview,
  getProjectReviewContext,
  getProjectReviewDecisions,
  getProjectReviews,
  getSubtasks,
  getTicketActivity,
  getTickets,
  login,
  logout,
  reviewTicketDraft,
  saveDrawerSession,
  submitFeedback,
  updateAcceptanceCriterion,
  updateMyWorkPreference,
  updateSubtask,
} from './api'

vi.mock('./api', () => ({
  acceptAIReview: vi.fn(),
  applyProjectReview: vi.fn(),
  createAcceptanceCriterion: vi.fn(),
  createAIReview: vi.fn(),
  createProject: vi.fn(),
  createProjectReview: vi.fn(),
  createSubtask: vi.fn(),
  createTicket: vi.fn(),
  createTicketUpdate: vi.fn(),
  deleteAcceptanceCriterion: vi.fn(),
  deleteSubtask: vi.fn(),
  downloadTicketExport: vi.fn(),
  getAcceptanceCriteria: vi.fn(),
  getCurrentSession: vi.fn(),
  getCurrentWorkIntake: vi.fn(),
  getWorkIntake: vi.fn(),
  cancelWorkIntake: vi.fn(),
  dismissWorkIntake: vi.fn(),
  proposeWorkIntake: vi.fn(),
  getDeploymentAdministratorAccess: vi.fn(),
  getFeedbackReviewerAccess: vi.fn(),
  getFeedbackDetail: vi.fn(),
  getFeedbackQueue: vi.fn(),
  getFeedbackScreenshot: vi.fn(),
  getIntakeReviewerAccess: vi.fn(),
  getPreferences: vi.fn(),
  getOnboarding: vi.fn(),
  updateOnboarding: vi.fn(),
  getReportProjects: vi.fn(),
  generateActivityReport: vi.fn(),
  savePreferences: vi.fn(),
  getProjects: vi.fn(),
  getMyWork: vi.fn(),
  getProjectWorkOverview: vi.fn(),
  getProjectReviewApplicationPreview: vi.fn(),
  getProjectReviewContext: vi.fn(),
  getProjectReviewDecisions: vi.fn(),
  makeProjectReviewFocus: vi.fn(),
  getProjectReviews: vi.fn(),
  saveProjectReviewDecision: vi.fn(),
  undoProjectReviewFocus: vi.fn(),
  getSubtasks: vi.fn(),
  getTicketActivity: vi.fn(),
  getTickets: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  reviewTicketDraft: vi.fn(),
  saveDrawerSession: vi.fn(),
  submitFeedback: vi.fn(),
  searchWork: vi.fn(),
  updateAcceptanceCriterion: vi.fn(),
  updateMyWorkPreference: vi.fn(),
  updateProject: vi.fn(),
  updateProjectAIContextPolicy: vi.fn(),
  updateSubtask: vi.fn(),
  updateFeedbackReview: vi.fn(),
  updateTicket: vi.fn(),
}))

const projects = [
  {
    id: 1,
    name: 'Telaryn Development',
    description: 'Development and testing of Telaryn.',
  },
]

const tickets = [
  {
    id: 22,
    public_id: 'TKT-7H4K-9M2P-6R8W',
    workspace_ticket_number: 7,
    title: 'Refactor the frontend',
    description: 'Reduce frontend coupling without changing behavior.',
    status: 'in_progress',
    priority: 'high',
    ticket_type: 'development',
    project_id: 1,
    updated_at: '2026-08-22T05:00:00+02:00',
  },
  {
    id: 23,
    workspace_ticket_number: 23,
    title: 'Centralize API logging',
    description: 'Add privacy-safe operational logging.',
    status: 'blocked',
    priority: 'medium',
    ticket_type: 'development',
    project_id: 1,
    updated_at: '2026-08-22T04:00:00+02:00',
  },
  {
    id: 21,
    title: 'Completed ticket',
    description: 'This should not appear on the Dashboard.',
    status: 'done',
    priority: 'high',
    ticket_type: 'development',
    project_id: 1,
    updated_at: '2026-08-21T04:00:00+02:00',
  },
  {
    id: 14,
    title: 'Cancelled ticket',
    description: 'This should not appear on the Dashboard.',
    status: 'cancelled',
    priority: 'medium',
    ticket_type: 'task',
    project_id: 1,
    updated_at: '2026-08-20T04:00:00+02:00',
  },
]

function arrangeApi() {
  getOnboarding.mockResolvedValue({
    dismissed: true,
    completed: false,
    show_panel: false,
    milestones: [],
  })
  getCurrentWorkIntake.mockResolvedValue(null)
  getCurrentSession.mockResolvedValue({ id: 1, email: 'jay@example.com', display_name: 'Jay', workspace_id: 1, workspace_name: "Jay's Workspace" })
  getDeploymentAdministratorAccess.mockResolvedValue({ allowed: false })
  getFeedbackReviewerAccess.mockResolvedValue({ allowed: false })
  getFeedbackQueue.mockResolvedValue({ items: [], total: 0, page: 1, pages: 1 })
  submitFeedback.mockResolvedValue({ reference: 'FBK-2222-3333-4444', status: 'new', submitted_at: '2026-09-20T06:04:40Z' })
  getIntakeReviewerAccess.mockResolvedValue({ allowed: false, new_count: 0 })
  getTickets.mockResolvedValue(tickets)
  getPreferences.mockResolvedValue({ default_project_id: null })
  savePreferences.mockImplementation(async id => ({ default_project_id: id }))
  getProjects.mockResolvedValue(projects)
  getReportProjects.mockResolvedValue([])
  getProjectReviews.mockResolvedValue([])
  getProjectReviewDecisions.mockResolvedValue([])
  getProjectReviewContext.mockResolvedValue({
    snapshot_version: 'snapshot-current',
  })
  getProjectWorkOverview.mockResolvedValue({
    project_id: 1,
    generated_at: '2026-08-24T12:00:00Z',
    tickets: { total: 4, active: 2, ready: 0, in_progress: 1, blocked: 1, review: 0, done: 1, cancelled: 1 },
    acceptance_criteria: { completed: 3, total: 5, deferred: 1 },
    subtasks: { completed: 4, total: 6, deferred: 2 },
    attention: [{ id: 23, workspace_ticket_number: 23, title: 'Centralize API logging', status: 'blocked', priority: 'medium', updated_at: '2026-08-22T04:00:00+02:00', reasons: ['Blocked'] }],
  })
  getMyWork.mockResolvedValue({
    generated_at: '2026-08-26T12:00:00Z',
    current_focus: {
      id: 22, workspace_ticket_number: 7, title: 'Refactor the frontend', project_id: 1,
      project_name: 'Telaryn Development',
      project_why_it_matters: 'Keep Telaryn maintainable as it grows.',
      project_target_date: '2026-11-01',
      description: 'Reduce frontend coupling so Telaryn stays maintainable.',
      focus_rationale: 'Work is already underway. It is marked high priority. It addresses: Reduce frontend coupling so Telaryn stays maintainable. Remaining scope: 1 of 3 acceptance criteria and 1 of 2 subtasks.',
      status: 'in_progress', priority: 'high',
      updated_at: '2026-08-22T05:00:00+02:00',
      reasons: ['Resume work already in progress'],
      acceptance_criteria: { completed: 2, total: 3 },
      subtasks: { completed: 1, total: 2 },
      next_action: { subtask_id: 7, title: 'Extract the next component', status: 'todo' },
      availability_mode: 'available', available_on: null,
    },
    suggestions: [],
    upcoming: [],
    focus_now: [],
    needs_attention: [{
      id: 23, workspace_ticket_number: 23, title: 'Centralize API logging', project_id: 1,
      project_name: 'Telaryn Development', status: 'blocked', priority: 'medium',
      updated_at: '2026-08-22T04:00:00+02:00', reasons: ['Blocked'],
      acceptance_criteria: { completed: 0, total: 1 },
      subtasks: { completed: 0, total: 1 },
      next_action: null, availability_mode: 'available', available_on: null,
    }],
    up_next: [],
    ready_later_count: 0,
    in_review: [],
    recently_completed: [],
  })
  updateMyWorkPreference.mockImplementation(async () => getMyWork.mock.results[0]?.value)
  getSubtasks.mockResolvedValue([])
  getAcceptanceCriteria.mockResolvedValue([])
  getTicketActivity.mockResolvedValue([])
  createAcceptanceCriterion.mockResolvedValue({})
  createSubtask.mockResolvedValue({})
}

async function renderAtlas() {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('heading', { name: 'Your next move, clearly.' })
  return user
}

describe('Telaryn application smoke tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
    arrangeApi()
  })

  test('restores the authenticated view and ticket without submitting interrupted edits', async () => {
    window.sessionStorage.setItem('atlas-location:1:1', JSON.stringify({
      view: 'about', ticketId: 22, projectId: 1, interruptedEdits: true,
    }))
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Close ticket' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Every action has a purpose.' })).toBeInTheDocument()
    expect(await screen.findByText(/Unsaved edits from before the reload were not recovered/)).toBeInTheDocument()
    expect(getSubtasks).toHaveBeenCalledWith(22)
    expect(saveDrawerSession).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Close ticket' }))
    await waitFor(() => {
      expect(JSON.parse(window.sessionStorage.getItem('atlas-location:1:1')).ticketId).toBeNull()
    })
  })


  test('recovers a manual New Ticket draft without creating it and clears it on cancel', async () => {
    window.sessionStorage.setItem('atlas-new-ticket:1:1', JSON.stringify({
      savedAt: Date.now(),
      form: { title: 'Phone draft', description: 'Keep this context', priority: 'medium', ticket_type: 'task', project_id: 1 },
      criteria: ['A saved criterion'], subtasks: [{ title: 'A saved subtask', description: null }],
      criterionInput: 'Unfinished criterion', subtaskInput: 'Unfinished subtask',
    }))
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByLabelText('Title')).toHaveValue('Phone draft')
    expect(screen.getByLabelText('Description')).toHaveValue('Keep this context')
    expect(screen.getByPlaceholderText('Add one criterion, or paste one per line...')).toHaveValue('Unfinished criterion')
    expect(screen.getByPlaceholderText('Add one subtask, or paste one per line...')).toHaveValue('Unfinished subtask')
    expect(createTicket).not.toHaveBeenCalled()
    const closeButton = screen.getByRole('button', { name: 'Close ticket' })
    expect(closeButton).toHaveAttribute('type', 'button')
    expect(closeButton).toHaveClass('ticket-modal-close')
    expect(screen.getByRole('checkbox', { name: /Make this Ticket Private/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    await waitFor(() => expect(window.sessionStorage.getItem('atlas-new-ticket:1:1')).toBeNull())
  })

  test('uses a five-slot mobile navigation and dismisses More on outside tap and Escape', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
    try {
      const user = userEvent.setup()
      render(<App />)
      const navigation = await screen.findByRole('navigation', { name: 'Mobile navigation' })
      expect([...navigation.querySelectorAll(':scope > button, :scope > details > summary')].map((item) => item.textContent)).toEqual([
        '✓Work', '▦Projects', '+New', '⌕Search', '•••More',
      ])
      const more = within(navigation).getByText('More').closest('summary')
      await user.click(more)
      expect(more.closest('details')).toHaveAttribute('open')
      expect(within(navigation).getByRole('button', { name: 'Reports' })).toBeInTheDocument()
      expect(within(navigation).getByRole('button', { name: 'Send Feedback' })).toBeInTheDocument()
      await user.click(screen.getByRole('main'))
      expect(more.closest('details')).not.toHaveAttribute('open')
      await user.click(more)
      await user.keyboard('{Escape}')
      expect(more.closest('details')).not.toHaveAttribute('open')
    } finally {
      vi.unstubAllGlobals()
    }
  })

  test('requires a valid session and signs in without public registration', async () => {
    const unauthorized = new Error('Authentication required.')
    unauthorized.status = 401
    getCurrentSession.mockRejectedValueOnce(unauthorized)
    login.mockResolvedValue({ id: 1, email: 'jay@example.com', display_name: 'Jay', workspace_id: 1, workspace_name: "Jay's Workspace" })
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Every action has a purpose.' })).toBeInTheDocument()
    expect(screen.getByText((_, element) => (
      element?.classList?.contains('public-hero-principle')
      && element.textContent === 'AI proposes. Humans approve. Telaryn records. Privacy protects every step.'
    ))).toBeInTheDocument()
    expect(screen.queryByText('Refactor the frontend')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sign In to Your Workspace' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back.' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back to Telaryn' }))
    expect(await screen.findByRole('heading', { name: 'Every action has a purpose.' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sign In to Your Workspace' }))
    await user.type(screen.getByLabelText('Email'), 'jay@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct horse battery staple')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(login).toHaveBeenCalledWith('jay@example.com', 'correct horse battery staple')
    expect(await screen.findByRole('heading', { name: 'Your next move, clearly.' })).toBeInTheDocument()
    expect(screen.queryByText(/register/i)).not.toBeInTheDocument()
  })

  test('publishes the RC1 identity, stable policy links, and support contacts before sign-in', async () => {
    const unauthorized = new Error('Authentication required.')
    unauthorized.status = 401
    getCurrentSession.mockRejectedValueOnce(unauthorized)
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Every action has a purpose.' })).toBeInTheDocument()
    expect(screen.getAllByText('v1.0.0-rc.1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Build development').length).toBeGreaterThan(0)
    expect(screen.getByText('© 2026 Jay Hughes. All rights reserved.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Support' })).toHaveAttribute('href', 'mailto:support@telaryn.app')
    expect(screen.getByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
    expect(screen.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms')
    expect(screen.getByRole('link', { name: 'About Telaryn' })).toHaveAttribute('href', '/about')
  })

  test('signs out and returns to the private login screen', async () => {
    logout.mockResolvedValue(null)
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Sign Out' }))

    expect(logout).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: 'Every action has a purpose.' })).toBeInTheDocument()
  })

  test('opens My Work without Dashboard navigation', async () => {
    await renderAtlas()
    expect(screen.queryByRole('button', { name: 'Dashboard' })).not.toBeInTheDocument()
    expect(screen.getByText('Refactor the frontend')).toBeInTheDocument()
  })

  test('navigates and highlights My Work sections from the sidebar', async () => {
    const scrollIntoView = vi.fn();
    const originalScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scrollIntoView;
    const user = await renderAtlas();

    const sectionNavigation = screen.getByRole('group', { name: 'My Work sections' });
    expect(within(sectionNavigation).getAllByRole('button').map((button) => button.textContent)).toEqual([
      'Current Focus',
      'Suggested Next',
      'Capture Work',
      'Needs Attention',
      'Recent Progress',
    ]);

    await user.click(within(sectionNavigation).getByRole('button', { name: 'Capture Work' }));
    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'start',
      });
    });
    expect(within(sectionNavigation).getByRole('button', { name: 'Capture Work' }))
      .toHaveAttribute('aria-current', 'location');

    const mobileSectionSelect = screen.getByLabelText('Jump to My Work section');
    expect(within(mobileSectionSelect).getAllByRole('option')).toHaveLength(5);
    await user.selectOptions(mobileSectionSelect, 'needs-attention');
    await waitFor(() => {
      expect(within(sectionNavigation).getByRole('button', { name: 'Needs Attention' }))
        .toHaveAttribute('aria-current', 'location');
    });

    Element.prototype.scrollIntoView = originalScrollIntoView;
  });

  test('updates the active My Work section at the bottom of the scroll surface', async () => {
    await renderAtlas();
    const scrollPanel = document.querySelector('.my-work-view');
    Object.defineProperties(scrollPanel, {
      clientHeight: { configurable: true, value: 600 },
      scrollHeight: { configurable: true, value: 1800 },
      scrollTop: { configurable: true, value: 1200, writable: true },
    });
    document.querySelectorAll('[data-my-work-section]').forEach((section, index) => {
      section.getBoundingClientRect = () => ({
        top: index * 320,
        bottom: index * 320 + 240,
        left: 0,
        right: 800,
        width: 800,
        height: 240,
        x: 0,
        y: index * 320,
        toJSON: () => ({}),
      });
    });

    fireEvent.scroll(scrollPanel);

    const sectionNavigation = screen.getByRole('group', { name: 'My Work sections' });
    await waitFor(() => {
      expect(within(sectionNavigation).getByRole('button', { name: 'Recent Progress' }))
        .toHaveAttribute('aria-current', 'location');
    });
  });

  test('navigates among the existing top-level views', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'My Work' }))
    expect(
      screen.getByRole('heading', { name: 'Your next move, clearly.' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Projects' }))
    expect(
      screen.getByRole('heading', { name: 'See the bigger picture.' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Settings' }))
    expect(
      screen.getByRole('heading', { name: 'Make Telaryn yours.' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Send Feedback' }))
    expect(screen.getByRole('heading', { name: 'Help us improve Telaryn.' })).toBeInTheDocument()
    expect(screen.getByText(/visible only to authorized feedback reviewers/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('heading', { name: 'Make Telaryn yours.' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'About Telaryn' }))
    expect(
      screen.getByRole('heading', {
        name: 'Every action has a purpose.',
      }),
    ).toBeInTheDocument()
  })

  test('shows Feedback Review only after feedback-reviewer authorization', async () => {
    getFeedbackReviewerAccess.mockResolvedValue({ allowed: true })
    const user = await renderAtlas()

    const review = await screen.findByRole('button', { name: 'Feedback Review' })
    await user.click(review)

    expect(await screen.findByRole('heading', { name: 'User Feedback' })).toBeInTheDocument()
    expect(getFeedbackQueue).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Back to My Work/ }).closest('main'))
      .toHaveClass('administration-view')
  })

  test('keeps Feedback Review independent from deployment administration', async () => {
    getDeploymentAdministratorAccess.mockResolvedValue({ allowed: true })
    getFeedbackReviewerAccess.mockResolvedValue({ allowed: false })
    await renderAtlas()

    expect(await screen.findByRole('button', { name: 'User Management' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Feedback Review' })).not.toBeInTheDocument()
  })

  test('turns My Work into a reasoned cross-project execution surface', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'My Work' }))

    expect(await screen.findByRole('heading', { name: 'Refactor the frontend' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Other meaningful options' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Clear the friction' })).toBeInTheDocument()
    expect(screen.getByText('Extract the next component')).toBeInTheDocument()
    expect(screen.getByText(/It addresses: Reduce frontend coupling so Telaryn stays maintainable\./)).toBeInTheDocument()
    expect(screen.queryByText('Keep Telaryn maintainable as it grows.')).not.toBeInTheDocument()
    expect(screen.getAllByText('Blocked')).toHaveLength(2)
    expect(screen.queryByLabelText('Current project')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    expect(await screen.findByText('Acceptance criteria')).toBeInTheDocument()
  })

  test('selects a project and opens its existing edit workflow', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(
      screen.getByRole('button', { name: /Telaryn Development/ }),
    )

    expect(
      screen.getByRole('heading', { name: 'Telaryn Development', level: 2 }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Completed ticket')).not.toBeInTheDocument()
    expect(screen.queryByText('Cancelled ticket')).not.toBeInTheDocument()

    const ticketVisibility = screen.getByLabelText('Ticket visibility')
    await user.click(within(ticketVisibility).getByRole('button', { name: 'All' }))
    expect(screen.getByText('Completed ticket')).toBeInTheDocument()
    expect(screen.getByText('Cancelled ticket')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Edit Project' }))

    expect(screen.getByPlaceholderText('Project name')).toHaveValue(
      'Telaryn Development',
    )
  })

  test('opens Project Review in its own selected-project section', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }))
    await user.click(screen.getByRole('button', { name: 'Telaryn AI Review' }))

    expect(
      await screen.findByRole('heading', {
        name: 'Step back and review the whole project.',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Review Project with Telaryn' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Current Snapshot' }),
    ).not.toBeInTheDocument()
  })

  test('preserves expanded Telaryn Review state while switching project tabs', async () => {
    getProjectReviews.mockResolvedValue([{
      id: 9,
      project_id: 1,
      snapshot_version: 'snapshot-current',
      status: 'completed',
      result: {
        outcome: 'no_material_concerns',
        summary: 'The project is healthy and ready for continued execution.',
        findings: [],
        risks: [],
        planning_guidance: [],
        proposals: [],
        recommended_focus: null,
      },
      safe_error_category: null,
      created_at: '2026-08-28T08:00:00Z',
      completed_at: '2026-08-28T08:00:01Z',
    }])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }))
    await user.click(screen.getByRole('button', { name: 'Telaryn AI Review' }))
    await user.click(
      await screen.findByRole('button', { name: 'Open Full Review' }),
    )
    expect(
      screen.getByRole('button', { name: 'Close Full Review' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Project Overview' }))
    await user.click(screen.getByRole('button', { name: 'Telaryn AI Review' }))

    expect(
      screen.getByRole('button', { name: 'Close Full Review' }),
    ).toBeInTheDocument()
  })

  test('shows a read-only project work overview and opens attention tickets', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }))

    expect(await screen.findByRole('heading', { name: 'Current Snapshot' })).toBeInTheDocument()
    expect(screen.getByText('3/5')).toBeInTheDocument()
    expect(screen.getByText('4/6')).toBeInTheDocument()
    expect(screen.getAllByText('Deferred')).toHaveLength(2)
    expect(screen.getByText('Blocked', { selector: '.project-attention-reasons' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /TKT-023 Centralize API logging/ }))
    expect(await screen.findByRole('heading', { name: 'Centralize API logging', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('Telaryn Development', { selector: '.detail-section p:last-child' })).toBeInTheDocument()
  })

  test('creates a project through the existing modal workflow', async () => {
    const user = await renderAtlas()
    const createdProject = {
      id: 2,
      name: 'Personal Development',
      description: 'Track learning and personal growth.',
      purpose: 'Build skills that support a meaningful transition.',
      why_it_matters: 'The transition is already underway.',
      target_date: '2026-11-01',
    }
    createProject.mockResolvedValue(createdProject)

    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(screen.getByRole('button', { name: '+ New Project' }))
    await user.type(
      screen.getByPlaceholderText('Project name'),
      'Personal Development',
    )
    await user.type(
      screen.getByPlaceholderText('Describe the project...'),
      'Track learning and personal growth.',
    )
    await user.type(
      screen.getByPlaceholderText('The outcome you want...'),
      'Build skills that support a meaningful transition.',
    )
    await user.type(
      screen.getByPlaceholderText('Why this deserves attention now...'),
      'The transition is already underway.',
    )
    await user.type(screen.getByLabelText(/Target date/), '2026-11-01')
    await user.click(screen.getByRole('button', { name: 'Create Project' }))

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledWith({
        name: 'Personal Development',
        description: 'Track learning and personal growth.',
        purpose: 'Build skills that support a meaningful transition.',
        why_it_matters: 'The transition is already underway.',
        target_date: '2026-11-01',
        life_context: 'unclassified',
      })
    })
    expect(
      screen.getByRole('heading', { name: 'Personal Development', level: 2 }),
    ).toBeInTheDocument()
  })

  test('clears Capture Work after creating a directly proposed Ticket', async () => {
    getCurrentWorkIntake
      .mockResolvedValueOnce({
      id: 92,
      source_text: 'Prepare the quarterly workspace access review.',
      status: 'completed',
      result: {
        action: 'create_ticket',
        summary: 'Create a workspace access review Ticket.',
        rationale: 'This is one bounded deliverable.',
        confidence: 'high',
        target_project_id: 1,
        target_ticket_id: null,
        matched_projects: [],
        matched_tickets: [],
        proposed_project: null,
        proposed_tickets: [
          {
            title: 'Review quarterly workspace access',
            description: 'Validate current workspace access and document required changes.',
            priority: 'medium',
            ticket_type: 'task',
            project_id: 1,
            acceptance_criteria: [
              { text: 'Every active membership has been reviewed.', basis: 'supported' },
            ],
            subtasks: [
              { text: 'Export the current membership list.', basis: 'inferred' },
            ],
          },
        ],
        proposed_ticket_changes: null,
        questions: [],
      },
    })
      .mockResolvedValue(null);
    createTicket.mockResolvedValue({
      id: 53,
      title: 'Review quarterly workspace access',
      description: 'Validate current workspace access and document required changes.',
      status: 'ready',
      priority: 'medium',
      ticket_type: 'task',
      project_id: 1,
    });
    const user = await renderAtlas();

    expect(await screen.findByText('Create a workspace access review Ticket.')).toBeInTheDocument();
    expect(screen.getAllByText('supported').length).toBeGreaterThan(0);
    expect(screen.getAllByText('inferred').length).toBeGreaterThan(0);
    await user.click(screen.getByRole('button', { name: 'Continue to Ticket Draft' }));
    expect(await screen.findByLabelText('Title')).toHaveValue('Review quarterly workspace access');

    await user.click(screen.getByRole('button', { name: 'Create Ticket' }));

    await waitFor(() => {
      expect(createTicket).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Review quarterly workspace access',
        project_id: 1,
      }));
      expect(screen.queryByText('Create a workspace access review Ticket.')).not.toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Capture New Work' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Close ticket' }));
    await user.click(screen.getByRole('button', { name: 'Projects' }));
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }));

    const createdHeading = screen.getByRole('heading', {
      name: 'Review quarterly workspace access',
      level: 3,
    });
    const olderHeading = screen.getByRole('heading', {
      name: 'Centralize API logging',
      level: 3,
    });
    expect(
      createdHeading.compareDocumentPosition(olderHeading)
        & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  test('reviews every guided starter Ticket after creating its Project', async () => {
    getCurrentWorkIntake.mockResolvedValue({
      id: 91,
      source_text: 'Create a repeatable employee onboarding process.',
      status: 'completed',
      result: {
        action: 'create_project',
        summary: 'Create an employee onboarding Project.',
        rationale: 'The outcome requires multiple coordinated deliverables.',
        confidence: 'high',
        target_project_id: null,
        target_ticket_id: null,
        matched_projects: [],
        matched_tickets: [],
        proposed_project: {
          name: 'Employee Onboarding',
          description: 'Create a repeatable onboarding process.',
          purpose: 'Give every new employee a consistent start.',
          why_it_matters: 'Access and training are currently inconsistent.',
        },
        proposed_tickets: [
          {
            title: 'Define the onboarding checklist',
            description: 'Document the required onboarding steps.',
            priority: 'high',
            ticket_type: 'task',
            project_id: null,
            acceptance_criteria: ['Required access and training are covered.'],
            subtasks: ['Interview the hiring manager.'],
          },
          {
            title: 'Pilot the onboarding process',
            description: 'Run the process with one new employee.',
            priority: 'medium',
            ticket_type: 'task',
            project_id: null,
            acceptance_criteria: ['Pilot feedback is documented.'],
            subtasks: ['Choose the pilot participant.'],
          },
        ],
        proposed_ticket_changes: null,
        questions: [],
      },
    });
    createProject.mockResolvedValue({
      id: 5,
      name: 'Employee Onboarding',
      description: 'Create a repeatable onboarding process.',
    });
    createTicket
      .mockResolvedValueOnce({
        id: 51,
        title: 'Define the onboarding checklist',
        description: 'Document the required onboarding steps.',
        status: 'ready',
        priority: 'high',
        ticket_type: 'task',
        project_id: 5,
      })
      .mockResolvedValueOnce({
        id: 52,
        title: 'Pilot the onboarding process',
        description: 'Run the process with one new employee.',
        status: 'ready',
        priority: 'medium',
        ticket_type: 'task',
        project_id: 5,
      });
    const user = await renderAtlas();

    await user.click(await screen.findByRole('button', { name: 'Continue to Project Draft' }));
    expect(screen.getByText(/Telaryn will open 2 proposed Tickets for your review/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Create Project' }));

    expect(await screen.findByLabelText('Title')).toHaveValue('Define the onboarding checklist');
    expect(screen.getByRole('status')).toHaveTextContent('Ticket 1 of 2');
    expect(screen.getByLabelText('Project')).toHaveValue('5');

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByRole('dialog', { name: 'What should happen to this proposal?' })).toBeInTheDocument();
    expect(screen.getByText(/Project and any Tickets already created will stay in place/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Keep Reviewing' }));
    expect(screen.getByRole('status')).toHaveTextContent('Ticket 1 of 2');
    expect(screen.getAllByText('Required access and training are covered.').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Interview the hiring manager.').length).toBeGreaterThan(0);

    await user.click(screen.getByRole('button', { name: 'Create Ticket' }));
    await waitFor(() => {
      expect(createTicket).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Define the onboarding checklist',
        project_id: 5,
        acceptance_criteria: [
          { text: 'Required access and training are covered.', sort_order: 1 },
        ],
        subtasks: [
          { title: 'Interview the hiring manager.', description: null, sort_order: 1 },
        ],
      }));
    });

    expect(await screen.findByLabelText('Title')).toHaveValue('Pilot the onboarding process');
    expect(screen.getByRole('status')).toHaveTextContent('Ticket 2 of 2');
    expect(screen.getByLabelText('Project')).toHaveValue('5');
    expect(screen.getAllByText('Pilot feedback is documented.').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Choose the pilot participant.').length).toBeGreaterThan(0);

    await user.click(screen.getByRole('button', { name: 'Create Ticket' }));

    await waitFor(() => {
      expect(createTicket).toHaveBeenLastCalledWith(expect.objectContaining({
        title: 'Pilot the onboarding process',
        project_id: 5,
      }));
      expect(screen.queryByRole('heading', { name: 'What needs to get done?' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Projects' })).toHaveClass('active');
    });
    expect(screen.getByRole('heading', { name: 'Employee Onboarding', level: 2 })).toBeInTheDocument();
  });

  test('changes and persists the selected appearance theme', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Settings' }))
    await user.click(screen.getByRole('button', { name: /Light/ }))

    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe('light')
      expect(window.localStorage.getItem('atlas-theme')).toBe('light')
    })
    expect(screen.getByRole('button', { name: /Light/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  test('uses the server default independently of the browsed project', async () => {
    getProjects.mockResolvedValue([...projects, { id: 2, name: 'Personal Development' }])
    getPreferences.mockResolvedValue({ default_project_id: 2 })
    const user = await renderAtlas()
    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }))
    await user.click(screen.getByRole('button', { name: '+ New Ticket' }))
    expect(screen.getByLabelText('Project')).toHaveValue('2')
    expect(savePreferences).not.toHaveBeenCalled()
  })

  test('explicitly imports and clears the previous browser default', async () => {
    window.localStorage.setItem('atlas-current-project-id', '1')
    const user = await renderAtlas()
    await user.click(screen.getByRole('button', { name: 'Projects' }))
    expect(savePreferences).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }))
    expect(screen.queryByLabelText('Default project')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Make Default Project' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Default Project' })).toHaveAttribute('aria-pressed', 'true'))
    await user.click(screen.getByRole('button', { name: 'Default Project' }))
    await waitFor(() => expect(savePreferences).toHaveBeenLastCalledWith(null))
  })

  test('falls back to no project for an unavailable default', async () => {
    getPreferences.mockResolvedValue({ default_project_id: 999 })
    const user = await renderAtlas()
    await user.click(screen.getByRole('button', { name: '+ New Ticket' }))
    expect(screen.getByLabelText('Project')).toHaveValue('')
  })

  test('retains the confirmed default when saving fails', async () => {
    getPreferences.mockResolvedValue({ default_project_id: 1 })
    savePreferences.mockRejectedValueOnce(new Error('Unable to save'))
    const user = await renderAtlas()
    await user.click(screen.getByRole('button', { name: 'Projects' }))
    await user.click(screen.getByRole('button', { name: /Telaryn Development/ }))
    await user.click(screen.getByRole('button', { name: 'Default Project' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to save')
    expect(screen.getByRole('button', { name: 'Default Project' }))
      .toHaveAttribute('aria-pressed', 'true')
  })

  test('opens and closes the ticket drawer with its close controls', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(
      await screen.findByRole('button', { name: 'Close ticket' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Review w/ Telaryn AI' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Close ticket' }))

    await waitFor(() => {
      expect(
        screen.queryByRole('button', { name: 'Close ticket' }),
      ).not.toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Open' }))
    expect(
      await screen.findByRole('button', { name: 'Close ticket' }),
    ).toBeInTheDocument()

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(
        screen.queryByRole('button', { name: 'Close ticket' }),
      ).not.toBeInTheDocument()
    })
  })

  test('keeps related ticket sections veiled until every initial request settles', async () => {
    let resolveSubtasks
    getSubtasks.mockImplementationOnce(() => new Promise((resolve) => {
      resolveSubtasks = resolve
    }))
    getAcceptanceCriteria.mockResolvedValueOnce([
      { id: 1, text: 'The drawer reveals complete content.', completed: false, deferred: false },
    ])

    const user = await renderAtlas()
    await user.click(screen.getByRole('button', { name: 'Open' }))

    const drawer = document.querySelector('.ticket-drawer')
    expect(within(drawer).getByRole('heading', { name: 'Refactor the frontend' })).toBeInTheDocument()
    expect(within(drawer).getByRole('status')).toHaveTextContent('Loading activity and planned work')
    expect(within(drawer).queryByText('Acceptance criteria')).not.toBeInTheDocument()
    expect(within(drawer).queryByText('Activity · 0')).not.toBeInTheDocument()

    resolveSubtasks([])

    await waitFor(() => {
      expect(within(drawer).queryByRole('status')).not.toBeInTheDocument()
    })
    expect(within(drawer).getByText('Acceptance criteria')).toBeInTheDocument()
    expect(within(drawer).getByText('The drawer reveals complete content.')).toBeInTheDocument()
    expect(within(drawer).getByText('Activity · 0')).toBeInTheDocument()
  })

  test('reveals actionable request failures after every initial request settles', async () => {
    getSubtasks.mockRejectedValueOnce(new Error('Subtasks are temporarily unavailable.'))
    getTicketActivity.mockRejectedValueOnce(new Error('Activity is temporarily unavailable.'))
    getAcceptanceCriteria.mockResolvedValueOnce([
      { id: 1, text: 'Successful collections remain visible.', completed: false, deferred: false },
    ])

    const user = await renderAtlas()
    await user.click(screen.getByRole('button', { name: 'Open' }))

    const drawer = document.querySelector('.ticket-drawer')
    expect(await within(drawer).findByRole('alert')).toHaveTextContent(
      'Some ticket details could not be loaded.',
    )
    expect(within(drawer).getByText('Subtasks are temporarily unavailable.')).toBeInTheDocument()
    expect(within(drawer).getByText('Activity is temporarily unavailable.')).toBeInTheDocument()
    expect(within(drawer).getByText('Successful collections remain visible.')).toBeInTheDocument()

    await user.click(within(drawer).getByRole('button', { name: 'Retry Ticket Details' }))

    await waitFor(() => {
      expect(within(drawer).queryByRole('alert')).not.toBeInTheDocument()
    })
    expect(within(drawer).getByText('Activity · 0')).toBeInTheDocument()
    expect(within(drawer).getByText('No subtasks yet.')).toBeInTheDocument()
  })

  test('edits and saves the ticket core details', async () => {
    const user = await renderAtlas()
    const updatedTicket = {
      ...tickets[0],
      title: 'Clarify frontend boundaries',
      description: 'Document the next safe extraction boundary.',
      priority: 'medium',
      ticket_type: 'task',
      project_id: null,
    }
    saveDrawerSession.mockResolvedValue({
      ticket: updatedTicket,
      acceptance_criteria: [],
      subtasks: [],
    })

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))

    await user.clear(screen.getByLabelText('Ticket title'))
    await user.type(
      screen.getByLabelText('Ticket title'),
      'Clarify frontend boundaries',
    )
    await user.selectOptions(screen.getByLabelText('Priority'), 'medium')
    await user.selectOptions(screen.getByLabelText('Ticket type'), 'task')
    await user.selectOptions(screen.getByLabelText('Project'), '')
    await user.clear(screen.getByLabelText('Description'))
    await user.type(
      screen.getByLabelText('Description'),
      'Document the next safe extraction boundary.',
    )
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))
    expect(await screen.findByRole('heading', { name: 'Review Ticket Update' })).toBeInTheDocument()
    expect(screen.queryByText('5 pending changes')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Commit Changes' }))

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, {
        ticket: {
          title: 'Clarify frontend boundaries',
          description: 'Document the next safe extraction boundary.',
          priority: 'medium',
          ticket_type: 'task',
          status: 'in_progress',
          project_id: null,
        },
        acceptance_criteria: [],
        subtasks: [],
        note: null,
        update_content: null,
      })
    })
    expect(
      screen.getByRole('heading', {
        name: 'Clarify frontend boundaries',
        level: 2,
      }),
    ).toBeInTheDocument()
  })

  test('keeps the staged review close control reachable without discarding changes', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))
    await user.clear(screen.getByLabelText('Ticket title'))
    await user.type(screen.getByLabelText('Ticket title'), 'Keep this staged title')
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))

    expect(await screen.findByRole('heading', { name: 'Review Ticket Update' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Close ticket' })).not.toBeInTheDocument()
    expect(screen.queryByText('1 pending change')).not.toBeInTheDocument()
    screen.getByLabelText('Update Note (optional)').focus()
    fireEvent.pointerDown(
      screen.getByRole('button', { name: 'Close ticket update review' }),
      { pointerType: 'touch' },
    )

    expect(screen.queryByRole('heading', { name: 'Review Ticket Update' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close ticket' })).toBeInTheDocument()
    expect(screen.getByText('1 pending change')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review Ticket Update' })).toBeInTheDocument()
  })

  test('expands a long editable ticket title when Edit Ticket focuses it', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))

    const title = screen.getByLabelText('Ticket title')
    expect(title).toHaveAttribute('title', 'Refactor the frontend')
    await waitFor(() => expect(title).toHaveClass('is-focused'))

    await user.tab()
    expect(title).not.toHaveClass('is-focused')
  })

  test('carries a drafted Ticket Update into reviewed atomic changes', async () => {
    const criterion = { id: 1, text: 'Record the outcome', completed: false, sort_order: 1 }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    saveDrawerSession.mockResolvedValue({
      ticket: tickets[0],
      acceptance_criteria: [{ ...criterion, completed: true }],
      subtasks: [],
    })
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: /Add Update/ }))
    await user.type(screen.getByPlaceholderText('What changed, what did you learn, or what happens next?'), 'Documented the completed outcome.')
    await user.click(screen.getByTitle('Mark complete'))
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))

    expect(screen.getByLabelText(/Update Note/)).toHaveValue('Documented the completed outcome.')
    expect(screen.getByText('A drafted Ticket Update will be recorded with this commit.')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Ticket outcome'), 'keep')
    await user.click(screen.getByRole('button', { name: 'Commit Changes' }))

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, expect.objectContaining({
        note: 'Documented the completed outcome.',
        update_content: 'Documented the completed outcome.',
      }))
    })
  })


  test.each(['done', 'review'])('closes only a successful Done transition (%s)', async (status) => {
    const user = await renderAtlas()
    saveDrawerSession.mockResolvedValue({
      ticket: { ...tickets[0], status },
      acceptance_criteria: [],
      subtasks: [],
    })
    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Change Status' }))
    await user.selectOptions(screen.getByLabelText('New status'), status)
    expect(screen.getByRole('button', { name: 'Close ticket' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))
    await user.click(screen.getByRole('button', { name: 'Commit Changes' }))
    await waitFor(() => expect(saveDrawerSession).toHaveBeenCalled())
    if (status === 'done') {
      await waitFor(() => expect(screen.queryByRole('button', { name: 'Close ticket' })).not.toBeInTheDocument())
      expect(getMyWork).toHaveBeenCalled()
    } else {
      expect(screen.getByRole('button', { name: 'Close ticket' })).toBeInTheDocument()
    }
  })

  test('keeps Done changes available for retry when commit fails', async () => {
    const user = await renderAtlas()
    saveDrawerSession.mockRejectedValueOnce(new Error('Connection lost'))
    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Change Status' }))
    await user.selectOptions(screen.getByLabelText('New status'), 'done')
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))
    await user.click(screen.getByRole('button', { name: 'Commit Changes' }))
    expect(await screen.findByText(/Telaryn could not commit the drawer session: Connection lost/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close ticket' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review Ticket Update' })).toBeInTheDocument()
  })

  test('stages status and progress together with required context', async () => {
    const criterion = { id: 1, text: 'Confirm the API decision', completed: false, sort_order: 1 }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    getSubtasks.mockResolvedValue([{
      id: 2,
      title: 'Follow up on the API decision',
      description: null,
      status: 'todo',
      sort_order: 1,
    }])
    const user = await renderAtlas()
    const updatedTicket = { ...tickets[0], status: 'blocked' }
    saveDrawerSession.mockResolvedValue({
      ticket: updatedTicket,
      acceptance_criteria: [{ ...criterion, completed: true }],
      subtasks: [],
    })

    await user.click(screen.getByRole('button', { name: 'Open' }))
    const criterionSection = screen.getByText('Acceptance criteria').closest('section')
    await user.click(within(criterionSection).getByTitle('Mark complete'))
    expect(screen.getByRole('button', { name: 'Change Status' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Change Status' }))
    expect(screen.queryByText('1 pending change')).not.toBeInTheDocument()
    const statusSelect = screen.getByLabelText('New status')
    expect(statusSelect).toBeInTheDocument()
    await user.selectOptions(statusSelect, 'blocked')
    expect(screen.getByText('2 pending changes')).toBeInTheDocument()
    expect(screen.queryByLabelText('New status')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))
    expect(screen.getByText('Acceptance Criterion Met')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    const commit = screen.getByRole('button', { name: 'Commit Changes' })
    expect(commit).toBeDisabled()
    await user.type(
      screen.getByLabelText(/Update Note/),
      'Waiting on an API decision.',
    )
    await user.click(commit)

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, expect.objectContaining({
        ticket: expect.objectContaining({ status: 'blocked' }),
        acceptance_criteria: [expect.objectContaining({ completed: true })],
        note: 'Waiting on an API decision.',
      }))
    })
    expect(screen.getByText('blocked', { selector: '.status-badge' })).toBeInTheDocument()
  })

  test('defaults the ticket to Done when the final active scope is resolved', async () => {
    const criterion = {
      id: 1,
      text: 'Confirm the final behavior',
      completed: false,
      deferred: false,
      sort_order: 1,
    }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    const updatedTicket = { ...tickets[0], status: 'done' }
    saveDrawerSession.mockResolvedValue({
      ticket: updatedTicket,
      acceptance_criteria: [{ ...criterion, completed: true }],
      subtasks: [],
    })
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByTitle('Mark complete'))
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))

    expect(screen.getByText('All active planned work has been resolved')).toBeInTheDocument()
    expect(screen.getAllByText('Confirm the final behavior')).toHaveLength(2)
    expect(screen.getByLabelText('Ticket outcome')).toHaveValue('done')
    const resolution = screen.getByText('All active planned work has been resolved').closest('section')
    const updateNote = screen.getByLabelText(/Update Note/).closest('label')
    const capturedChanges = screen.getByText('Acceptance Criterion Met').closest('ul')
    expect(updateNote.parentElement).toHaveClass('drawer-staging-pinned')
    expect(
      resolution.compareDocumentPosition(updateNote)
      & resolution.ownerDocument.defaultView.Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      updateNote.compareDocumentPosition(capturedChanges)
      & updateNote.ownerDocument.defaultView.Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    const commit = screen.getByRole('button', { name: 'Commit Changes' })
    expect(commit).toBeEnabled()
    await user.click(commit)

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, expect.objectContaining({
        ticket: expect.objectContaining({ status: 'done' }),
        acceptance_criteria: [expect.objectContaining({
          id: 1,
          completed: true,
        })],
      }))
    })
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Close ticket' })).not.toBeInTheDocument()
    })
  })

  test('expands unified ticket activity and records a new update', async () => {
    const updateItems = [
      {
        source_type: 'ticket_update',
        source_id: 4,
        event_type: 'ticket_update_added',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: null,
        content: 'Most recent progress',
        note: null,
        created_at: '2026-08-22T08:00:00+02:00',
        attachment_count: 0,
      },
      {
        source_type: 'ticket_update',
        source_id: 3,
        event_type: 'ticket_update_added',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: null,
        content: 'Third update',
        note: null,
        created_at: '2026-08-22T07:00:00+02:00',
        attachment_count: 0,
      },
      {
        source_type: 'ticket_update',
        source_id: 2,
        event_type: 'ticket_update_added',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: null,
        content: 'Second update',
        note: null,
        created_at: '2026-08-22T06:00:00+02:00',
        attachment_count: 0,
      },
      {
        source_type: 'ticket_update',
        source_id: 1,
        event_type: 'ticket_update_added',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: null,
        content: 'Oldest update',
        note: null,
        created_at: '2026-08-22T05:00:00+02:00',
        attachment_count: 0,
      },
    ]
    const statusItems = [
      {
        source_type: 'status_event',
        source_id: 2,
        event_type: 'status_changed',
        actor_type: 'local_user',
        actor_id: null,
        field_name: 'status',
        previous_value: 'blocked',
        new_value: 'in_progress',
        note: 'Work resumed.',
        content: null,
        attachment_count: 0,
        created_at: '2026-08-22T08:30:00+02:00',
      },
      {
        source_type: 'status_event',
        source_id: 1,
        event_type: 'status_changed',
        actor_type: 'local_user',
        actor_id: null,
        field_name: 'status',
        previous_value: 'ready',
        new_value: 'blocked',
        note: 'Waiting on a decision.',
        content: null,
        attachment_count: 0,
        created_at: '2026-08-22T04:30:00+02:00',
      },
    ]
    const createdUpdate = {
      id: 5,
      content: 'Recorded after the extraction.',
      created_at: '2026-08-22T09:00:00+02:00',
      attachment_count: 0,
    }
    const initialActivity = [statusItems[0], ...updateItems, statusItems[1]]
    getTicketActivity
      .mockResolvedValueOnce(initialActivity)
      .mockResolvedValueOnce([
        {
          source_type: 'ticket_update',
          source_id: 5,
          event_type: 'ticket_update_added',
          actor_type: 'local_user',
          actor_id: null,
          field_name: null,
          previous_value: null,
          new_value: null,
          note: null,
          ...createdUpdate,
        },
        ...initialActivity,
      ])
    createTicketUpdate.mockResolvedValue(createdUpdate)
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(screen.getByText('Work resumed.')).toBeInTheDocument()
    expect(screen.queryByText('Oldest update')).not.toBeInTheDocument()
    expect(screen.queryByText('Waiting on a decision.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Show History' }))
    expect(screen.getByText('Oldest update')).toBeInTheDocument()
    expect(screen.getByText('Waiting on a decision.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '+ Add Update' }))
    await user.type(
      screen.getByPlaceholderText(
        'What changed, what did you learn, or what happens next?',
      ),
      'Recorded after the extraction.',
    )
    await user.click(screen.getByRole('button', { name: 'Record Update' }))

    await waitFor(() => {
      expect(createTicketUpdate).toHaveBeenCalledWith(22, {
        content: 'Recorded after the extraction.',
      })
    })
    expect(screen.getByText('Recorded after the extraction.')).toBeInTheDocument()
  })

  test('distinguishes authenticated people from legacy local activity', async () => {
    getTicketActivity.mockResolvedValue([
      {
        source_type: 'ticket_update',
        source_id: 2,
        event_type: 'ticket_update_added',
        actor_type: 'user',
        actor_id: '1',
        actor_name: 'Jay',
        content: 'Authenticated update',
        created_at: '2026-08-22T09:00:00+02:00',
        attachment_count: 0,
      },
      {
        source_type: 'ticket_update',
        source_id: 1,
        event_type: 'ticket_update_added',
        actor_type: 'local_user',
        actor_id: null,
        actor_name: null,
        content: 'Historical update',
        created_at: '2026-08-22T08:00:00+02:00',
        attachment_count: 0,
      },
    ])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(screen.getByText('Jay', { selector: '.activity-meta span' })).toBeInTheDocument()
    expect(screen.getByText('Legacy local activity')).toBeInTheDocument()
  })

  test.each(['done', 'cancelled'])('stages completion toggles and commits %s when closing the drawer', async (outcome) => {
    const criterion = {
      id: 1,
      text: 'The extraction preserves behavior.',
      completed: false,
      sort_order: 1,
    }
    const subtask = {
      id: 1,
      title: 'Extract the structure sections',
      description: 'Move presentation without moving API ownership.',
      status: 'todo',
      sort_order: 1,
    }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    getSubtasks.mockResolvedValue([subtask])
    saveDrawerSession.mockResolvedValue({
      ticket: tickets[0],
      acceptance_criteria: [{ ...criterion, completed: true }],
      subtasks: [{ ...subtask, status: 'done' }],
    })
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getAllByTitle('Mark complete')[0])
    await user.click(screen.getAllByTitle('Mark complete')[0])
    expect(screen.getByText('2 pending changes')).toBeInTheDocument()
    expect(screen.queryByLabelText('Ticket title')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Add Subtask' })).not.toBeInTheDocument()
    expect(updateAcceptanceCriterion).not.toHaveBeenCalled()
    expect(updateSubtask).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Close ticket' }))
    expect(await screen.findByRole('heading', { name: 'Review Ticket Update' })).toBeInTheDocument()
    expect(screen.getByText('All active planned work has been resolved')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Ticket outcome'), outcome)
    if (outcome === 'cancelled') {
      expect(screen.getByRole('button', { name: 'Commit Changes' })).toBeDisabled()
      expect(saveDrawerSession).not.toHaveBeenCalled()
      await user.type(screen.getByLabelText(/Update Note/), 'No longer required.')
    }
    await user.click(screen.getByRole('button', { name: 'Commit Changes' }))

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, expect.objectContaining({
        acceptance_criteria: [expect.objectContaining({ id: 1, completed: true })],
        subtasks: [expect.objectContaining({ id: 1, status: 'done' })],
        note: outcome === 'cancelled' ? 'No longer required.' : null,
        update_content: null,
      }))
    })
    expect(screen.queryByRole('button', { name: 'Close ticket' })).not.toBeInTheDocument()
  })

  test('hides progress actions when toggles return to their saved state', async () => {
    const criterion = {
      id: 1,
      text: 'No net change remains',
      completed: false,
      sort_order: 1,
    }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByTitle('Mark complete'))
    expect(screen.getByRole('button', { name: 'Undo Ticket Update' })).toBeInTheDocument()
    await user.click(screen.getByTitle('Mark incomplete'))

    expect(screen.queryByRole('button', { name: 'Undo Ticket Update' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Review Ticket Update' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review w/ Telaryn AI' })).toBeInTheDocument()
  })

  test('shows initial criteria and subtasks inside the ticket creation activity', async () => {
    getTicketActivity.mockResolvedValue([
      {
        source_type: 'activity_event',
        source_id: 1,
        event_type: 'ticket_created',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: {
          title: 'Refactor the frontend',
          acceptance_criteria: [
            { id: 1, text: 'Creation is grouped', completed: false },
          ],
          subtasks: [
            { id: 1, title: 'Verify activity', description: null, status: 'todo' },
          ],
        },
        content: null,
        note: null,
        attachment_count: 0,
        created_at: '2026-08-22T08:30:00+02:00',
      },
    ])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(
      screen.getByText('2 items created with ticket').closest('details'),
    ).toHaveAttribute('open')
    expect(screen.getByText(/Creation is grouped/)).toBeInTheDocument()
    expect(screen.getByText(/Verify activity/)).toBeInTheDocument()
  })

  test('collapses large ticket creation activity entries by default', async () => {
    getTicketActivity.mockResolvedValue([
      {
        source_type: 'activity_event',
        source_id: 2,
        event_type: 'ticket_created',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: {
          title: 'Large structured ticket',
          acceptance_criteria: [
            { id: 1, text: 'First criterion', completed: false },
            { id: 2, text: 'Second criterion', completed: false },
          ],
          subtasks: [
            { id: 1, title: 'First subtask', description: null, status: 'todo' },
            { id: 2, title: 'Second subtask', description: null, status: 'todo' },
          ],
        },
        content: null,
        note: null,
        attachment_count: 0,
        created_at: '2026-08-22T08:30:00+02:00',
      },
    ])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(
      screen.getByText('4 items created with ticket').closest('details'),
    ).not.toHaveAttribute('open')
  })

  test('collapses large grouped activity entries by default', async () => {
    getTicketActivity.mockResolvedValue([
      {
        source_type: 'activity_event',
        source_id: 7,
        event_type: 'drawer_session_committed',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: {
          ticket: { title: 'Old', description: null, priority: 'medium', status: 'ready' },
          acceptance_criteria: [],
          subtasks: [],
        },
        new_value: {
          ticket: { title: 'New', description: 'Context', priority: 'high', status: 'done' },
          acceptance_criteria: [],
          subtasks: [],
        },
        content: null,
        note: 'One grouped update.',
        attachment_count: 0,
        created_at: '2026-08-22T08:30:00+02:00',
      },
    ])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(screen.getByText('4 changes committed').closest('details')).not.toHaveAttribute('open')
    expect(screen.getByText('Ticket update committed')).toBeInTheDocument()
  })

  test('collapses a description-only drawer activity entry by default', async () => {
    getTicketActivity.mockResolvedValue([
      {
        source_type: 'activity_event',
        source_id: 8,
        event_type: 'drawer_session_committed',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: {
          ticket: { description: 'Short original description.' },
          acceptance_criteria: [],
          subtasks: [],
        },
        new_value: {
          ticket: { description: 'A much longer revised description that should stay tucked away.' },
          acceptance_criteria: [],
          subtasks: [],
        },
        content: null,
        note: 'Clarified the ticket context.',
        attachment_count: 0,
        created_at: '2026-08-22T08:30:00+02:00',
      },
    ])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    expect(screen.getByText('Description changed').closest('details')).not.toHaveAttribute('open')
    expect(screen.getByText('Clarified the ticket context.')).toBeInTheDocument()
  })

  test('limits long activity updates to three lines until expanded', async () => {
    const longUpdate = 'Documented a detailed implementation decision, the alternatives considered, the reason for the selected approach, the validation performed, and the follow-up work that remains so the complete context stays available without dominating the ticket timeline.'
    getTicketActivity.mockResolvedValue([
      {
        source_type: 'ticket_update',
        source_id: 9,
        event_type: 'ticket_update_added',
        actor_type: 'local_user',
        actor_id: null,
        field_name: null,
        previous_value: null,
        new_value: null,
        content: longUpdate,
        note: null,
        attachment_count: 0,
        created_at: '2026-08-22T08:30:00+02:00',
      },
    ])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    const update = screen.getByText(longUpdate)
    const expandButton = screen.getByRole('button', { name: 'Show Full Update' })
    expect(update).toHaveClass('activity-update-clamped')
    expect(expandButton).toHaveAttribute('aria-expanded', 'false')

    await user.click(expandButton)

    expect(update).not.toHaveClass('activity-update-clamped')
    expect(screen.getByRole('button', { name: 'Show Less' })).toHaveAttribute('aria-expanded', 'true')
  })

  test('requires an update when completed work is reopened', async () => {
    const criterion = {
      id: 1,
      text: 'Previously met criterion',
      completed: true,
      sort_order: 1,
    }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    saveDrawerSession.mockResolvedValue({
      ticket: tickets[0],
      acceptance_criteria: [{ ...criterion, completed: false }],
      subtasks: [],
    })
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByTitle('Mark incomplete'))
    await user.click(screen.getByRole('button', { name: 'Close ticket' }))

    expect(await screen.findByRole('heading', { name: 'Review Ticket Update' })).toBeInTheDocument()
    const commit = screen.getByRole('button', { name: 'Commit Changes' })
    expect(commit).toBeDisabled()
    await user.type(screen.getByLabelText(/Update Note/), 'New evidence invalidated this criterion.')
    await user.click(commit)

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, expect.objectContaining({
        acceptance_criteria: [expect.objectContaining({ id: 1, completed: false })],
        note: 'New evidence invalidated this criterion.',
      }))
    })
  })

  test('defers scope with a required reason and excludes it from active progress', async () => {
    const criterion = {
      id: 1,
      text: 'Ship CSV import',
      completed: false,
      deferred: false,
      deferred_reason: null,
      sort_order: 1,
    }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    saveDrawerSession.mockResolvedValue({
      ticket: tickets[0],
      acceptance_criteria: [{
        ...criterion,
        deferred: true,
        deferred_reason: 'Moved to the import project.',
      }],
      subtasks: [],
    })
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    const section = screen.getByText('Acceptance criteria').closest('section')
    await user.click(within(section).getByRole('button', { name: 'Defer' }))
    expect(within(section).getByText('0/0 · 1 deferred')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))

    const commit = screen.getByRole('button', { name: 'Commit Changes' })
    expect(commit).toBeDisabled()
    await user.selectOptions(screen.getByLabelText('Ticket outcome'), 'keep')
    await user.type(screen.getByLabelText(/Update Note/), 'Moved to the import project.')
    await user.click(commit)

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, expect.objectContaining({
        acceptance_criteria: [expect.objectContaining({ id: 1, deferred: true })],
        note: 'Moved to the import project.',
      }))
    })
    expect(screen.getByText('Deferred Scope (1)')).toBeInTheDocument()
  })

  test('adds and saves staged acceptance criteria and subtasks', async () => {
    const criterion = {
      id: 1,
      text: 'Existing criterion',
      completed: false,
      sort_order: 1,
    }
    const subtask = {
      id: 1,
      title: 'Existing subtask',
      description: null,
      status: 'todo',
      sort_order: 1,
    }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    getSubtasks.mockResolvedValue([subtask])
    saveDrawerSession.mockResolvedValue({
      ticket: tickets[0],
      acceptance_criteria: [criterion, { id: 2, text: 'New criterion', completed: false, sort_order: 2 }],
      subtasks: [subtask, { id: 2, title: 'New subtask', description: 'New context', status: 'todo', sort_order: 2 }],
    })
    updateAcceptanceCriterion.mockResolvedValue(criterion)
    updateSubtask.mockResolvedValue(subtask)
    createAcceptanceCriterion.mockResolvedValue({})
    createSubtask.mockResolvedValue({})
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))
    let section = screen.getByText('Acceptance criteria').closest('section')
    await user.click(within(section).getByRole('button', { name: '+ Add Acceptance Criterion' }))
    await user.type(
      within(section).getByLabelText('New acceptance criterion'),
      'New criterion',
    )
    await user.click(within(section).getByRole('button', { name: 'Add Acceptance Criterion' }))
    section = screen.getByText('Subtasks').closest('section')
    await user.click(within(section).getByRole('button', { name: '+ Add Subtask' }))
    await user.type(within(section).getByLabelText('Subtask 2 title'), 'New subtask')
    await user.type(
      within(section).getByLabelText('Description (optional)'),
      'New context',
    )
    await user.click(within(section).getByRole('button', { name: 'Add Subtask' }))
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))
    expect(await screen.findByRole('heading', { name: 'Review Ticket Update' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Commit Changes' }))

    await waitFor(() => {
      expect(saveDrawerSession).toHaveBeenCalledWith(22, {
        ticket: {
          title: 'Refactor the frontend',
          description: 'Reduce frontend coupling without changing behavior.',
          priority: 'high',
          ticket_type: 'development',
          status: 'in_progress',
          project_id: 1,
        },
        acceptance_criteria: [
          { id: 1, text: 'Existing criterion', completed: false, deferred: false },
          { id: null, text: 'New criterion', completed: false, deferred: false },
        ],
        subtasks: [
          { id: 1, title: 'Existing subtask', description: null, status: 'todo' },
          { id: null, title: 'New subtask', description: 'New context', status: 'todo' },
        ],
        note: null,
        update_content: null,
      })
    })
  })

  test('makes drawer bulk structure entry discoverable in full-width composers', async () => {
    getAcceptanceCriteria.mockResolvedValue([])
    getSubtasks.mockResolvedValue([])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))

    let section = screen.getByText('Acceptance criteria').closest('section')
    const addCriterion = within(section).getByRole('button', { name: '+ Add Acceptance Criterion' })
    expect(addCriterion).toHaveClass('empty-structure-add-button')
    await user.click(addCriterion)
    const criterionInput = within(section).getByLabelText('New acceptance criterion')
    expect(criterionInput.closest('form')).toHaveClass('structure-add-editor')
    expect(within(section).getByText('Enter one item per line. Paste a list to add several at once.')).toBeInTheDocument()
    await user.type(criterionInput, 'First criterion{enter}Second criterion')
    expect(within(section).getByRole('button', { name: 'Add 2 Acceptance Criteria' })).toBeInTheDocument()

    section = screen.getByText('Subtasks').closest('section')
    const addSubtask = within(section).getByRole('button', { name: '+ Add Subtask' })
    expect(addSubtask).toHaveClass('empty-structure-add-button')
    await user.click(addSubtask)
    const subtaskInput = within(section).getByLabelText('Subtask 1 title')
    expect(subtaskInput.closest('.subtask-edit-row')).toHaveClass('structure-add-editor')
    expect(within(section).getByText('Enter one item per line. Paste a list to add several at once.')).toBeInTheDocument()
    await user.type(subtaskInput, 'First subtask{enter}Second subtask')
    expect(within(section).getByRole('button', { name: 'Add 2 Subtasks' })).toBeInTheDocument()
  })

  test('undoes staged acceptance-criteria edits before commit', async () => {
    const criterion = { id: 1, text: 'Original criterion', completed: false, sort_order: 1 }
    getAcceptanceCriteria.mockResolvedValue([criterion])
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))
    const section = screen.getByText('Acceptance criteria').closest('section')
    await user.click(within(section).getAllByRole('button', { name: 'Remove' })[0])
    await user.click(screen.getByRole('button', { name: 'Review Ticket Update' }))
    await user.click(await screen.findByRole('button', { name: 'Undo All Changes' }))

    expect(screen.getByText('Original criterion')).toBeInTheDocument()
    expect(createAcceptanceCriterion).not.toHaveBeenCalled()
  })

  test('reviews an existing ticket and applies only approved Telaryn suggestions', async () => {
    const review = {
      id: 9,
      provider: 'mock',
      reasoning_summary: 'The ticket can be clarified before implementation.',
      suggested_title: 'Refactor frontend presentation boundaries',
      suggested_description: 'Move stable presentation boundaries into components.',
      suggested_priority: 'medium',
      suggested_ticket_type: 'development',
      missing_information: [],
      recommendations: [],
      acceptance_criteria: [
        { text: 'The new component receives explicit props.', basis: 'supported' },
        { text: 'Do not apply this criterion.', basis: 'recommended' },
      ],
      suggested_subtasks: [
        {
          title: 'Extract the review panel',
          description: 'Keep proposal and approval state in App.',
          basis: 'inferred',
        },
      ],
    }
    createAIReview.mockResolvedValue(review)
    acceptAIReview.mockResolvedValue({})
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await user.click(screen.getByRole('button', { name: 'Review w/ Telaryn AI' }))
    expect(createAIReview).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Continue with AI' }))
    expect(
      await screen.findByRole('heading', { name: 'Suggested improvements' }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('supported').length).toBeGreaterThan(0)
    expect(screen.getAllByText('recommended').length).toBeGreaterThan(0)

    await user.click(
      screen.getByRole('checkbox', { name: 'Do not apply this criterion.' }),
    )
    await user.click(
      screen.getByRole('checkbox', { name: 'Create suggested subtasks' }),
    )
    await user.click(screen.getByRole('button', { name: 'Apply Suggestions' }))

    await waitFor(() => {
      expect(acceptAIReview).toHaveBeenCalledWith(22, 9, {
        apply_title: true,
        apply_description: true,
        apply_priority: true,
        apply_ticket_type: true,
        create_subtasks: false,
        acceptance_criteria_indices: [0],
      })
    })
    expect(
      screen.queryByRole('heading', { name: 'Suggested improvements' }),
    ).not.toBeInTheDocument()
  })

  test('creates a ticket with manual criteria and subtasks without AI review', async () => {
    const user = await renderAtlas()
    const createdTicket = {
      id: 25,
      title: 'Document the v0.1 release boundary',
      description: 'Define what finished means for the first usable release.',
      status: 'ready',
      priority: 'medium',
      ticket_type: 'task',
      project_id: null,
      updated_at: '2026-08-22T06:00:00+02:00',
    }
    createTicket.mockResolvedValue(createdTicket)

    await user.click(screen.getByRole('button', { name: '+ New Ticket' }))
    await user.type(
      screen.getByLabelText('Title'),
      'Document the v0.1 release boundary',
    )
    await user.type(
      screen.getByLabelText('Description'),
      'Define what finished means for the first usable release.',
    )
    await user.type(
      screen.getByPlaceholderText('Add one criterion, or paste one per line...'),
      'The v0.1 scope is documented.',
    )
    await user.click(screen.getByRole('button', { name: 'Add Acceptance Criterion' }))
    await user.type(
      screen.getByPlaceholderText('Add one subtask, or paste one per line...'),
      'Identify required tickets',
    )
    await user.click(screen.getByRole('button', { name: 'Add Subtask' }))

    await user.click(screen.getByRole('button', { name: 'Create Ticket' }))

    await waitFor(() => {
      expect(createTicket).toHaveBeenCalledWith({
        title: 'Document the v0.1 release boundary',
        description: 'Define what finished means for the first usable release.',
        priority: 'medium',
        ticket_type: 'task',
        project_id: null,
        acceptance_criteria: [
          { text: 'The v0.1 scope is documented.', sort_order: 1 },
        ],
        subtasks: [
          { title: 'Identify required tickets', description: null, sort_order: 1 },
        ],
      })
    })
    expect(createAcceptanceCriterion).not.toHaveBeenCalled()
    expect(createSubtask).not.toHaveBeenCalled()
    expect(reviewTicketDraft).not.toHaveBeenCalled()
  })

  test('cancels and retries draft review without losing the ticket draft', async () => {
    reviewTicketDraft.mockImplementation((_draft, { signal }) => (
      new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => {
          reject(new Error('AI Review was cancelled. Your work is unchanged.'))
        })
      })
    ))
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: '+ New Ticket' }))
    await user.type(screen.getByLabelText('Title'), 'Preserve this draft')
    await user.type(
      screen.getByLabelText('Description'),
      'This content must survive cancellation.',
    )
    await user.type(
      screen.getByPlaceholderText('Add one criterion, or paste one per line...'),
      'The saved result remains measurable.',
    )
    await user.click(screen.getByRole('button', { name: 'Add Acceptance Criterion' }))
    await user.type(
      screen.getByPlaceholderText('Add one subtask, or paste one per line...'),
      'Preserve the implementation step',
    )
    await user.click(screen.getByRole('button', { name: 'Add Subtask' }))
    await user.click(screen.getByRole('button', { name: /Review with Telaryn/ }))
    await user.click(screen.getByRole('button', { name: 'Continue with AI' }))
    await user.click(screen.getByRole('button', { name: 'Cancel Review' }))

    expect(
      await screen.findByText('AI Review was cancelled. Your work is unchanged.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Title')).toHaveValue('Preserve this draft')
    expect(screen.getByLabelText('Description')).toHaveValue(
      'This content must survive cancellation.',
    )
    expect(screen.getByText('The saved result remains measurable.')).toBeInTheDocument()
    expect(screen.getByText('Preserve the implementation step')).toBeInTheDocument()

    reviewTicketDraft.mockResolvedValue({
      provider: 'mock',
      suggested_title: null,
      suggested_description: null,
      suggested_priority: null,
      suggested_ticket_type: null,
      reasoning_summary: null,
      missing_information: [],
      recommendations: [],
      acceptance_criteria: [],
      suggested_subtasks: [],
      acceptance_criteria_revisions: [],
      subtask_revisions: [],
    })
    await user.click(screen.getByRole('button', { name: /Retry Review with Telaryn/ }))

    expect(
      await screen.findByRole('heading', { name: 'Choose what Telaryn should apply' }),
    ).toBeInTheDocument()
    expect(reviewTicketDraft).toHaveBeenCalledTimes(2)
  })

  test('reviews a rough draft and creates only selected Telaryn suggestions', async () => {
    const user = await renderAtlas()
    const draftReview = {
      provider: 'mock',
      suggested_title: 'Add the Projects cancelled-ticket toggle',
      suggested_description:
        'Let users choose whether cancelled tickets appear on Projects.',
      suggested_priority: 'medium',
      suggested_ticket_type: 'development',
      reasoning_summary: 'The rough draft describes a focused UI improvement.',
      missing_information: [],
      recommendations: [],
      acceptance_criteria: [
        { text: 'Cancelled tickets are hidden by default.', basis: 'inferred' },
        { text: 'Do not include this criterion.', basis: 'recommended' },
      ],
      suggested_subtasks: [
        {
          title: 'Add the visibility toggle',
          description: 'Add a clear control to the Projects ticket list.',
          basis: 'inferred',
        },
        {
          title: 'Do not create this subtask',
          description: 'This suggestion will be declined by the user.',
          basis: 'recommended',
        },
      ],
      acceptance_criteria_revisions: [],
      subtask_revisions: [],
    }
    const createdTicket = {
      id: 26,
      title: draftReview.suggested_title,
      description: draftReview.suggested_description,
      status: 'ready',
      priority: 'medium',
      ticket_type: 'development',
      project_id: null,
      updated_at: '2026-08-22T07:00:00+02:00',
    }
    reviewTicketDraft.mockResolvedValue(draftReview)
    createTicket.mockResolvedValue(createdTicket)

    await user.click(screen.getByRole('button', { name: '+ New Ticket' }))
    await user.type(screen.getByLabelText('Title'), 'Project ticket toggle')
    await user.type(
      screen.getByLabelText('Description'),
      'Maybe hide cancelled tickets unless I ask to see them.',
    )
    await user.click(screen.getByRole('button', { name: /Review with Telaryn/ }))
    await user.click(screen.getByRole('button', { name: 'Continue with AI' }))

    expect(
      await screen.findByRole('heading', {
        name: 'Choose what Telaryn should apply',
      }),
    ).toBeInTheDocument()
    expect(reviewTicketDraft).toHaveBeenCalledWith(
      {
        title: 'Project ticket toggle',
        description: 'Maybe hide cancelled tickets unless I ask to see them.',
        priority: 'medium',
        ticket_type: 'task',
        project_id: null,
        subtasks: [],
        acceptance_criteria: [],
      },
      { signal: expect.anything() },
    )

    await user.click(screen.getByRole('button', { name: 'Back to Draft' }))
    expect(screen.getByLabelText('Title')).toHaveValue('Project ticket toggle')
    await user.click(screen.getByRole('button', { name: /Review with Telaryn/ }))
    expect(
      await screen.findByRole('heading', {
        name: 'Choose what Telaryn should apply',
      }),
    ).toBeInTheDocument()
    expect(reviewTicketDraft).toHaveBeenCalledTimes(2)

    await user.click(
      screen.getByRole('checkbox', { name: 'Do not include this criterion.' }),
    )
    await user.click(
      screen.getByRole('checkbox', { name: /Do not create this subtask/ }),
    )
    await user.click(
      screen.getByRole('button', {
        name: 'Create Ticket & Selected Subtasks',
      }),
    )

    await waitFor(() => {
      expect(createTicket).toHaveBeenCalledWith({
        title: draftReview.suggested_title,
        description: draftReview.suggested_description,
        priority: 'medium',
        ticket_type: 'development',
        project_id: null,
        acceptance_criteria: [
          { text: 'Cancelled tickets are hidden by default.', sort_order: 1 },
        ],
        subtasks: [
          {
            title: 'Add the visibility toggle',
            description: 'Add a clear control to the Projects ticket list.',
            sort_order: 1,
          },
        ],
      })
    })
    expect(createAcceptanceCriterion).not.toHaveBeenCalled()
    expect(createSubtask).not.toHaveBeenCalled()
  })

  test('keeps the immutable public Ticket reference above drawer actions and terminal edit controls', async () => {
    const user = await renderAtlas()

    await user.click(screen.getByRole('button', { name: 'Open' }))

    const publicReference = screen.getByText('TKT-7H4K-9M2P-6R8W').closest('section')
    expect(publicReference).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy public Ticket reference' })).toHaveTextContent('Copy')

    const drawerAction = screen.getByRole('button', { name: 'Change Status' })
    expect(
      publicReference.compareDocumentPosition(drawerAction)
      & publicReference.ownerDocument.defaultView.Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Edit Ticket' }))
    const titleInput = screen.getByLabelText('Ticket title')
    await user.clear(titleInput)
    await user.type(titleInput, 'Refactor frontend boundaries')

    const terminalEditControl = screen.getByRole('button', { name: 'Review Ticket Update' })
    const drawerFooter = terminalEditControl.closest('.inline-edit-footer')
    expect(drawerFooter).toBeInTheDocument()
    expect(drawerFooter.parentElement).toHaveClass('ticket-drawer')
    expect(drawerFooter.previousElementSibling).toHaveClass('ticket-drawer-scroll')
    expect(
      publicReference.compareDocumentPosition(terminalEditControl)
      & publicReference.ownerDocument.defaultView.Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

})
