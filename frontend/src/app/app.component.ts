import { Component, inject, signal } from '@angular/core';
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
export class AppComponent {

  private readonly sessionService = inject(SessionService);
  private readonly chatService = inject(ChatService);

  title = 'frontend';

  private _socket: Socket | undefined = undefined;

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

  ngOnDestroy() {
    this.sessionService.endSession();
  }

  submitMessage() {
    const msg = this.userMessageValue + "";
    this.chatService.sendMessage(msg);
    this.messages.update((prev) => {
      const last_id = (prev.length == 0) ? 0 : prev[prev.length - 1].id;
      return [...prev, { id: last_id + 1, text: msg, botMessage: false }];
    })
    this.userMessageValue = '';
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
}
