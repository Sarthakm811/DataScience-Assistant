import { describe, expect, it, vi } from 'vitest'
import { datasetAPI } from '../services/api'

describe('dataset API', () => {
    it('uploads a file with cookie credentials and returns the dataset', async () => {
        const response = {
            ok: true,
            json: vi.fn().mockResolvedValue({ id: 'ds-1', rowCount: 2 })
        }
        global.fetch = vi.fn().mockResolvedValue(response)
        const file = new File(['value\n1\n2\n'], 'data.csv', { type: 'text/csv' })

        await expect(datasetAPI.uploadDataset(file)).resolves.toEqual({
            id: 'ds-1',
            rowCount: 2
        })

        expect(global.fetch).toHaveBeenCalledWith(
            '/api/datasets/upload',
            expect.objectContaining({
                method: 'POST',
                credentials: 'include',
                body: expect.any(FormData)
            })
        )
    })
})
