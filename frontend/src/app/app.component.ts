import { Component, inject, signal, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ChatService } from './chat.service';
import { Session, SessionService } from './session.service';
import { concatMap, EMPTY, Observable, Subscription, tap } from 'rxjs';
import { Socket } from 'socket.io-client';

interface Message {
  id: number,
  text: string,
  botMessage: boolean,
};

@Component({
  selector: 'app-root',
  imports: [],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements AfterViewChecked {

  private readonly sessionService = inject(SessionService);
  private readonly chatService = inject(ChatService);

  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('messageInput') messageInput!: ElementRef;

  title = 'frontend';

  private _socket: Socket | undefined = undefined;

  // Chatbot UI state
  isChatbotOpen = signal(false);
  isChatbotMinimized = signal(false);
  isOptionsMenuOpen = signal(false);
  showCloseModal = signal(false);

  // Chat state
  messages = signal<Message[]>([]);
  userMessageValue = '';

  ngOnInit() {
    this.sessionService.beginSession().pipe(
      concatMap(() => this.sessionService.session),
      tap({ complete: () => this.chatService.disconnect() }),
      concatMap((session) => session ? this.chatService.connect(session) : EMPTY)
    ).subscribe({
      next: (socket) => {
        this._socket = socket;
      },
      complete: () => {
        this.sessionService.endSession();
      }
    })

    this.chatService.botMessage$.subscribe({
      next: (message) => {
        this.messages.update((prev) => {
          const last_id = (prev.length == 0) ? 0 : prev[prev.length - 1].id;
          return [...prev, { id: last_id + 1, text: message, botMessage: true }];
        })
      }
    })
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  ngOnDestroy() {
    this.sessionService.endSession();
  }

  // Chatbot UI methods
  toggleChatbot() {
    this.isChatbotOpen.update(open => !open);
    this.isChatbotMinimized.set(false);
    this.isOptionsMenuOpen.set(false);
    
    // Focus input when opening chatbot
    if (this.isChatbotOpen()) {
      setTimeout(() => {
        if (this.messageInput?.nativeElement) {
          this.messageInput.nativeElement.focus();
        }
      }, 300);
    }
  }

  closeChatbot() {
    this.isChatbotOpen.set(false);
    this.isChatbotMinimized.set(false);
    this.isOptionsMenuOpen.set(false);
  }

  minimizeChatbot() {
    // Minimize functionality - this should minimize the entire chatbot, not just hide the body
    this.isChatbotOpen.set(false);
    this.isOptionsMenuOpen.set(false);
  }

  toggleOptionsMenu() {
    this.isOptionsMenuOpen.update(open => !open);
  }

  showCloseConfirmation() {
    this.showCloseModal.set(true);
    this.isOptionsMenuOpen.set(false);
  }

  hideCloseConfirmation() {
    this.showCloseModal.set(false);
  }

  confirmEndChat() {
    this.endChat();
    this.closeChatbot();
    this.showCloseModal.set(false); // Make sure to explicitly set this to false
  }

  // Chat functionality methods
  newChat() {
    this.messages.set([]);
    this.userMessageValue = '';
    this.isOptionsMenuOpen.set(false);
  }

  refreshChat() {
    // Refresh the current chat session
    this.isOptionsMenuOpen.set(false);
    // Add any refresh logic here if needed
    console.log('Refreshing chat...');
  }

  endChat() {
    this.messages.set([]);
    this.userMessageValue = '';
    this.isOptionsMenuOpen.set(false);
    
    // End the session
    this.sessionService.endSession();
    
    // Disconnect from chat service
    this.chatService.disconnect();
  }

  submitMessage() {
    const msg = this.userMessageValue.trim();
    if (!msg) return;

    this.chatService.sendMessage(msg);
    this.messages.update((prev) => {
      const last_id = (prev.length == 0) ? 0 : prev[prev.length - 1].id;
      return [...prev, { id: last_id + 1, text: msg, botMessage: false }];
    })
    this.userMessageValue = '';
    
    // Focus input after sending message
    setTimeout(() => {
      if (this.messageInput?.nativeElement) {
        this.messageInput.nativeElement.focus();
      }
    }, 100);
  }

  updateUserInput(event: Event) {
    const target = event.target as HTMLInputElement;
    if (!target) return;

    this.userMessageValue = target.value;
  }

  onSubmit(event: Event) {
    event.preventDefault();
    this.submitMessage();
  }

  private scrollToBottom() {
    if (this.messagesContainer?.nativeElement) {
      const container = this.messagesContainer.nativeElement;
      container.scrollTop = container.scrollHeight;
    }
  }

  // Handle keyboard shortcuts
  onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      if (this.showCloseModal()) {
        this.hideCloseConfirmation();
      } else if (this.isOptionsMenuOpen()) {
        this.isOptionsMenuOpen.set(false);
      } else if (this.isChatbotOpen()) {
        this.closeChatbot();
      }
    }
  }
}