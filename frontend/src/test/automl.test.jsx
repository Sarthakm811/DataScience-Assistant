import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AutoML from '../pages/AutoML'
import { AnalysisProvider } from '../context/AnalysisContext'

describe('AutoML flow', () => {
    it('posts the selected dataset, features, and target', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue({
                models: [{
                    model_id: 'model-1',
                    model_name: 'Linear Regression',
                    metrics: { r2: 0.9 }
                }]
            })
        })
        const dataset = {
            id: 'ds-1',
            name: 'data.csv',
            headers: ['feature', 'target'],
            rows: Array.from({ length: 25 }, (_, index) => ({
                feature: index + 1,
                target: (index + 1) * 2
            })),
            rowCount: 25,
            colCount: 2
        }

        render(
            <AnalysisProvider>
                <AutoML dataset={dataset} setDataset={vi.fn()} />
            </AnalysisProvider>
        )

        fireEvent.click(screen.getAllByRole('checkbox')[0])
        fireEvent.click(screen.getByRole('radio', { name: 'target' }))
        fireEvent.click(screen.getByRole('button', { name: 'Train Selected Model' }))

        await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
            '/api/ml/train-selected',
            expect.objectContaining({
                method: 'POST',
                credentials: 'include',
                body: expect.stringContaining('"dataset_id":"ds-1"')
            })
        ))
    })
})
