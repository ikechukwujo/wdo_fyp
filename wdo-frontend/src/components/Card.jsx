import clsx from 'clsx'
import styles from './Card.module.css'

export default function Card({ children, className, glow }) {
  return (
    <div className={clsx(styles.card, glow && styles.glow, className)}>
      {children}
    </div>
  )
}
